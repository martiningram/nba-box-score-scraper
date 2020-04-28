from os import makedirs
from os.path import join
from functions import (get_season_month_links, check_points_consistent,
                       parse_month)


base_url = 'https://www.basketball-reference.com'

years = range(1977, 2020)

seasons_to_parse = [base_url + f'/leagues/NBA_{year}_games.html' for year in
                    years]

target_dir = './results'

for cur_year, cur_season in zip(years, seasons_to_parse):

    cur_months = get_season_month_links(cur_season)

    for cur_month_link in cur_months:

        print(f'Parsing {cur_month_link}...')

        parsed_month = parse_month(base_url, cur_month_link)
        passes_total_check = check_points_consistent(parsed_month)
        parsed_month['points_ok'] = passes_total_check

        cur_target_dir = join(target_dir, str(cur_year))
        makedirs(cur_target_dir, exist_ok=True)

        cur_name = cur_month_link.split('/')[-1].split('.')[0]
        parsed_month.to_csv(join(cur_target_dir, f'{cur_name}.csv'))
