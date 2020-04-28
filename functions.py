import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from tqdm import tqdm
import numpy as np


def fetch_soup(url):

    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')

    return soup


def fetch_season_month_links(season_soup):

    all_links = season_soup.find_all('a', href=True)

    relevant = [x for x in all_links if 'games-' in x.get('href')]
    all_hrefs = [x.get('href') for x in relevant]

    return all_hrefs


def fetch_month_box_score_links(month_soup):

    hrefs = month_soup.find_all('a', href=True)
    box_scores = [x for x in hrefs if 'Box Score' in x.text]
    links = [x.get('href') for x in box_scores]

    return links


def get_date_strs_from_link(link):

    return datetime.strptime(link.split('/')[-1][:8], '%Y%m%d')


def parse_stats(table_row):

    player_name = table_row.find('th').text
    all_entries = table_row.find_all('td')

    names = [x.attrs['data-stat'] for x in all_entries]
    values = [x.text for x in all_entries]
    stats = {x: y for x, y in zip(names, values)}

    stats['name'] = player_name

    return stats


def try_to_parse(table_row):

    try:
        return parse_stats(table_row)
    except AttributeError:
        return {}


def find_team_names(box_score_soup):
    # I _think_ the first team is the away team, and the second is home?

    captions = box_score_soup.find_all('caption')

    team_names = [' '.join(x.text.split(' ')[:2]) for x in captions]

    return team_names


def assemble_stats_table(box_score_soup, date):

    parsing_results = [try_to_parse(x) for x in box_score_soup.find_all('tr')]

    # Drop empty names:
    valid_only = [x for x in parsing_results if len(x) > 0 and
                  len(x['name']) > 0 and x['name'] != 'Player']

    # Split by team totals
    all_names = [x['name'] for x in valid_only]
    totals_indices = [i for i, x in enumerate(all_names) if x == 'Team Totals']
    total_1, total_2 = totals_indices

    team_1_results = pd.DataFrame(valid_only[:total_1+1])
    team_2_results = pd.DataFrame(valid_only[total_1+1:])

    team_1_name, team_2_name = find_team_names(box_score_soup)

    team_1_results['team'] = team_1_name
    team_2_results['team'] = team_2_name

    # TODO: Check this -- may be wrong.
    team_1_results['is_home'] = False
    team_2_results['is_home'] = True

    combined = pd.concat([team_1_results, team_2_results])

    combined['date'] = date

    combined['game_id'] = ('_'.join(combined['team'].unique()) + '_' +
                           combined['date'].astype(str))

    return combined


def get_season_month_links(season_url):

    season_soup = fetch_soup(season_url)
    month_links = fetch_season_month_links(season_soup)

    return month_links


def parse_month(base_url, month_link):

    month_soup = fetch_soup(base_url + month_link)

    box_score_links = fetch_month_box_score_links(month_soup)

    dates = [get_date_strs_from_link(x) for x in box_score_links]

    all_tables = list()

    for cur_date, cur_link in zip(tqdm(dates), box_score_links):

        box_score_soup = fetch_soup(base_url + cur_link)

        cur_table = assemble_stats_table(box_score_soup, cur_date)

        all_tables.append(cur_table)

    return pd.concat(all_tables)


def check_points_consistent(parsed_month):

    # TODO: This function is useful but a bit messy. Maybe improve.
    summed_points = (parsed_month[
        parsed_month['name'] != 'Team Totals'].groupby(
        ['game_id', 'team'])['pts'].apply(
            lambda x: x.astype(float).sum())).values

    totals = parsed_month[
        parsed_month['name'] == 'Team Totals'].groupby(
        ['game_id', 'team'])['pts'].apply(
            lambda x: x.sum()).values.astype(float)

    return np.allclose(summed_points, totals)
