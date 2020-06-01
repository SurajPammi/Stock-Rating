import pandas as pd
import numpy as np
import urllib as u
from bs4 import BeautifulSoup as bs
import requests
import yfinance as yf
from yahoo_fin import stock_info as si
import datetime
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

MOST_RECENT_QUARTER = 0
NUMBER_OF_QUARTERS = 4
ASSERT_ERROR = AssertionError
KEY_ERROR = KeyError
INVALID_DASH = "-"
GOOD_Z = 3.0
BAD_Z = 1.8
QUICK_RATIO_MIDDLE = 1.0


def get_stock():
    ticker = input("Enter a stock: ")
    ticker = ticker.replace(" ", "")
    return ticker


def check_if_stock_is_valid(ticker):
    try:
        stock = yf.Ticker(ticker)
        stock.info
    except ASSERT_ERROR:
        print("Invalid stock ticker")
        return False
    except KEY_ERROR:
        print("Invalid stock ticker")
        return False
    return True


def get_basic_info(stock):
    information = stock.info
   # print(information)
    quarterly_financials = stock.quarterly_financials
    #print(quarterly_financials)
    quarterly_balance_sheet = stock.quarterly_balance_sheet
    #print(quarterly_balance_sheet)
    return information, quarterly_financials, quarterly_balance_sheet


def qb_qf_values(quarterly_balance_sheet, quarterly_financials):
    qf_list_column_one = quarterly_financials.index
    for i in range(len(qf_list_column_one)):
        if qf_list_column_one[i] == "Net Income":
            net_income_row = i
        if qf_list_column_one[i] == "Ebit":
            ebit_row = i
    qb_list_column_one = quarterly_balance_sheet.index
    for i in range(len(qb_list_column_one)):
        if qb_list_column_one[i] == "Total Assets":
            total_assets_row = i
        if qb_list_column_one[i] == "Total Liab":
            total_liab_row = i
        if qb_list_column_one[i] == "Retained Earnings":
            retained_earnings_row = i
        if qb_list_column_one[i] == "Total Current Liabilities":
            total_cur_liab_row = i
        if qb_list_column_one[i] == "Total Current Assets":
            total_cur_ass_row = i
    net_income_ttm = 0
    for i in range(4):
        r = quarterly_financials.iloc[net_income_row, int(i)]
        net_income_ttm = net_income_ttm + r
    recent_quarter_total_assets = quarterly_balance_sheet.iloc[total_assets_row, MOST_RECENT_QUARTER]
    #roa_ttm_percentage = (net_income_ttm / recent_quarter_total_assets) * 100
    total_liabilities = quarterly_balance_sheet.iloc[total_liab_row, MOST_RECENT_QUARTER]
    retained_earnings = quarterly_balance_sheet.iloc[retained_earnings_row, MOST_RECENT_QUARTER]
    total_current_liab = quarterly_balance_sheet.iloc[total_cur_liab_row, MOST_RECENT_QUARTER]
    total_cur_assets = quarterly_balance_sheet.iloc[total_cur_ass_row, MOST_RECENT_QUARTER]
    ebit = quarterly_financials.iloc[ebit_row,MOST_RECENT_QUARTER]
    return recent_quarter_total_assets, net_income_ttm, total_liabilities, retained_earnings, \
        total_current_liab, total_cur_assets, ebit


def scrape_finviz(ticker):
    link = "https://finviz.com/quote.ashx?t=" + ticker + "&ty=c&ta=1&p=d"
    indicators = ["P/B", "P/E", "Quick Ratio", "Current Ratio", "Debt/Eq", "Oper. Margin", "Dividend %", "Dividend",
                  "Forward P/E", "PEG", "P/S", "P/C", "P/FCF", "EPS (ttm)", "EPS next Y", "EPS next Q", "EPS this Y",
                  "EPS next 5Y", "EPS past 5Y", "Insider Own", "Insider Trans", "Inst Own", "Inst Trans", "Shs Outstand",
                  "Sales", "ROA", "ROE", "Profit Margin"]
    contents = u.request.urlopen(link).read()
    soup = bs(contents, 'lxml')
    # make this a for i loop later
    values_list = []
    for i in range(len(indicators)):
        line = soup.find(text=indicators[i])
        value = line.find_next(class_='snapshot-td2').text
        values_list.append(value)
        if indicators[i] == "EPS next Y":
            line = line.find_next(text="EPS next Y")
            eps_next_y_percent_value = line.find_next(class_='snapshot-td2').text
    values_list.append(eps_next_y_percent_value)
    return values_list


def convert_value(list_values):
    for i in range(len(list_values)):
        if list_values[i] == INVALID_DASH:
            list_values[i] = "0"
        if "B" in str(list_values[i]) or "M" in str(list_values[i]) or "T" in str(list_values[i]):
            list_values[i] = str(list_values[i]).replace("B", "0000000")
            list_values[i] = str(list_values[i]).replace("M", "0000")
            list_values[i] = str(list_values[i]).replace(".", "")

        if "%" in str(list_values[i]):
            list_values[i] = list_values[i][0:-1]
        list_values[i] = float(list_values[i])
    return list_values


def get_todays_date():
    now = datetime.datetime.now()
    return now


def dividend_rating(stock, ticker, now, annual_dividend):
    dividend_history = stock.dividends
    if str(dividend_history) == "Series([], Name: Dividends, dtype: int64)":
        dividend_yield = 0
        dividend_rating = 0
    else:
        dividend_history_column_one = (dividend_history.index)
        last_column = dividend_history_column_one[-1]
        year = (str(last_column)[0:4:])
        this_year = now.year
        last_year = (now.year - 1)

        if (str(this_year) not in year) and (str(last_year) not in year):
            dividend_yield = 0
            dividend_rating = 0
        else:
            last_year = []
            last_year_dividends = []

            for dividend in dividend_history_column_one:
                if dividend.year == (now.year) - 1:
                    last_year.append(str(dividend))
            for i in range(len(last_year)):
                for index, row in stock.dividends.iteritems():
                    if str(index) == str(last_year[i]):
                        last_year_dividends.append(row)
            last_year_annual_dividend = sum(last_year_dividends)

            current_stock_price = si.get_live_price(ticker)
            dividend_yield = (annual_dividend / current_stock_price) * 100

            all_annuals = []
            dividend_list_for_addition = []
            five_years_ago_dividend_list = []
            year = str(dividend_history_column_one[0])[0:4]
            five_years_ago = (now.year - 5)
            for index, row in dividend_history.iteritems():
                if str(index)[0:4] == str(now.year):
                    # COME BACK TO THIS PART
                    all_annuals.append(annual_dividend)
                    break
                if str(index)[0:4] == year:
                    dividend_list_for_addition.append(row)
                if str(index)[0:4] != year:
                    all_annuals.append(sum(dividend_list_for_addition))
                    dividend_list_for_addition = [row]
                if str(index)[0:4] == str(five_years_ago):
                    five_years_ago_dividend_list.append(row)
                year = str(index)[0:4]

            consecutive_annual_dividend_increases = 0
            for i in range(len(all_annuals) - 1, -1, -1):
                if all_annuals[i] > all_annuals[i - 1]:
                    consecutive_annual_dividend_increases += 1
                else:
                    break

            consecutive_annual_dividend_decreases = 0
            for i in range(len(all_annuals) - 1, -1, -1):
                if all_annuals[i] < all_annuals[i - 1]:
                    consecutive_annual_dividend_decreases += 1
                else:
                    break

            annual_dividend_staying_same = 0
            for i in range(len(all_annuals) - 1, -1, -1):
                if all_annuals[i] == all_annuals[(i - 1)]:
                    annual_dividend_staying_same += 1
                else:
                    break

            percents = []
            for i in range((len(all_annuals) - 1)):

                r = ((all_annuals[i + 1] - all_annuals[i]) / all_annuals[i]) * 100
                percents.append(r)
            last_five = percents[-5::]
            last_five_annual_changes = sum(last_five) / len(last_five)

            if dividend_yield <= .25:
                dividend_rating = 1
            elif .25 < dividend_yield <= .5:
                dividend_rating = 2
            elif .5 < dividend_yield < .75:
                dividend_rating = 2.5
            elif .75 < dividend_yield < 1:
                dividend_rating = 2.75
            elif 1 <= dividend_yield <= 1.5:
                dividend_rating = 3
            elif 1.5 < dividend_yield <= 2:
                dividend_rating = 4
            elif 2 < dividend_yield <= 3:
                dividend_rating = 5
            elif 3 < dividend_yield <= 3.5:
                dividend_rating = 6
            elif 3.5 < dividend_yield <= 4:
                dividend_rating = 7
            elif 4 < dividend_yield <= 5.5:
                dividend_rating = 8
            elif 5.5 < dividend_yield <= 6:
                dividend_rating = 9
            elif dividend_yield > 6:
                dividend_rating = 10
            if consecutive_annual_dividend_increases >= 1:
                dividend_rating += 1
            elif consecutive_annual_dividend_decreases >= 1:
                dividend_rating -= 1
            if dividend_rating >= 10:
                dividend_rating = 10
            if last_five_annual_changes >= 10:
                dividend_rating += 3
            elif 10 > last_five_annual_changes >= 5:
                dividend_rating += 2
            elif 5 > last_five_annual_changes > 0:
                dividend_rating += 1
            elif last_five_annual_changes >= -10:
                dividend_rating -= 3
            elif -10 > last_five_annual_changes >= -5:
                dividend_rating -= 2
            elif -5 > last_five_annual_changes >= 0:
                dividend_rating -= 1
            return dividend_rating, dividend_yield, consecutive_annual_dividend_increases, \
                consecutive_annual_dividend_decreases, annual_dividend_staying_same, last_five_annual_changes
    return 0, 0, 0, 0, 0, 0


def analyst_recommendations(stock, ticker, now):
    stock_recommendations = stock.recommendations
    error_flag = False
    try:
        dates = stock_recommendations.index
    except AttributeError:
        error_flag = True
    months = []
    if error_flag is False:
        date_list = []
        month = int(now.month)
        while len(months) != 13:
            months.append(month)
            if month == 12:
                month = 0
            month += 1
        rs = 12 - int(now.month)
        for date in dates:
            if date.month in months:
                if (date.year == (now.year - 1) and date.month in months[:(rs+1):]) or date.year == now.year:
                    date_list.append(str(date))
        firms_this_year = []
        firm_rating_this_year = []
        non_duplicate_dates = []
        if len(date_list) != 0:
            for dates in date_list:
                if dates not in non_duplicate_dates:
                    non_duplicate_dates.append(dates)
            for i in range(len(non_duplicate_dates)):
                for index, row in stock_recommendations.iterrows():
                    if str(index) == str(non_duplicate_dates[i]):
                        firms_this_year.append(row[0])
                        firm_rating_this_year.append(row[1])

            non_duplicate_firms = []
            non_duplicate_firm_rating = []
            for i in range((len(firms_this_year) - 1), -1, -1):
                if firms_this_year[i] not in non_duplicate_firms:
                    non_duplicate_firms.append(firms_this_year[i])
                    non_duplicate_firm_rating.append(firm_rating_this_year[i])
                else:
                    date_list.remove(date_list[i])
            date_list.reverse()
            # scrape zacks too
            modified_ratings = []
            for rating in non_duplicate_firm_rating:
                if rating == "Equal-Weight" or rating == "Accumulate" or rating == "Neutral" \
                        or rating == "Market Perform" or rating == "Hold":
                    modified_ratings.append("Hold")
                if rating == "Buy" or rating == "Outperform" or rating == "Overweight" or rating == "Positive":
                    modified_ratings.append("Buy")
                if rating == "Sell" or rating == "Underweight" or rating == "Underperform":
                    modified_ratings.append("Sell")
            buy_count = 0
            hold_count = 0
            sell_count = 0
            for rating in modified_ratings:
                if rating == "Buy":
                    buy_count += 1
                if rating == "Hold":
                    hold_count += 1
                if rating == "Sell":
                    sell_count += 1
            number_of_ratings = len(modified_ratings)
            return number_of_ratings, sell_count, buy_count, hold_count, non_duplicate_firms, date_list
    return 0, 0, 0, 0, 0, 0


def institutional_values(stock, ins_own, ins_trans, inst_own, inst_trans):
    # major_holders = stock.major_holders
    # print(major_holders)
    return ins_own, ins_trans, inst_own, inst_trans


def growth_rating(stock, eps_ttm, eps_next_y, eps_next_q, eps_this_y, eps_next_five_y, eps_past_five_y, eps_next_y_percent):
    # revenue section
    # incorporate revenue rating in growth rating
    growth_rating = 0
    revenue_rating = 0
    yearly_earnings = stock.earnings
    quarterly_earnings = stock.quarterly_earnings
    average_annual_revenue_growth = []
    one = ((yearly_earnings.iloc[1, 0] - yearly_earnings.iloc[0, 0]) / yearly_earnings.iloc[0, 0]) * 100
    two = ((yearly_earnings.iloc[2, 0] - yearly_earnings.iloc[1, 0]) / yearly_earnings.iloc[1, 0]) * 100
    three = ((yearly_earnings.iloc[3, 0] - yearly_earnings.iloc[2, 0]) / yearly_earnings.iloc[2, 0]) * 100
    average_annual_revenue_growth.append(one)
    average_annual_revenue_growth.append(two)
    average_annual_revenue_growth.append(three)

    four_year_revenue_change = (sum(average_annual_revenue_growth) / len(average_annual_revenue_growth))

    four_quarter_revenue_change = (((quarterly_earnings.iloc[-1, 0] - quarterly_earnings.iloc[0, 0])
                                    / quarterly_earnings.iloc[0, 0]) * 100)
    #last_quarter_revenue_to_current_change = (((quarterly_earnings.iloc[-1, 0] - quarterly_earnings.iloc[-2, 0])
                                              # / quarterly_earnings.iloc[-2, 0]) * 100)

    revenues = [four_year_revenue_change, four_quarter_revenue_change]

    for revenue in revenues:
        if revenue < -10:
            growth_rating -= 2
        elif -10 <= revenue < 0:
            growth_rating -= 1
        elif 10 > revenue > 0:
            growth_rating += .5
        elif 20 > revenue >= 10:
           growth_rating += 1
        elif 30 >= revenue >= 20:
            growth_rating += 1.25
        elif revenue > 30:
            growth_rating += 2

    # EPS ratings
    eps_list = [eps_next_y_percent, eps_this_y, eps_next_five_y, eps_past_five_y]
    for eps in eps_list:
        if eps < -10:
            growth_rating -= 2
        elif -10 <= eps < 0:
            growth_rating -= 1
        elif 10 >= eps > 0:
            growth_rating += .25
        elif 20 >= eps > 10:
            growth_rating += .5
        elif 25 > eps > 20:
            growth_rating += 1
        elif eps >= 25:
            growth_rating += 1.5

    if growth_rating > 10:
        growth_rating = 10

    return growth_rating, eps_ttm, eps_next_y, eps_next_q, eps_this_y, eps_next_five_y, eps_past_five_y, \
        four_year_revenue_change, four_quarter_revenue_change, eps_next_y_percent


def value_rating(stock):

    return


def calculate_z_score(net_income, sales, shs_out, retained_earnings, total_current_liabilities, total_current_assets,
                      total_assets, total_liabilities, ebit):
    # Z-Score = 1.2A + 1.4B + 3.3C + 0.6D + 1.0E
    #A = working capital / total assets
    working_capital = total_current_assets - total_current_liabilities
    a_ = working_capital / total_assets
    #B = retained earnings / total assets
    b_ = retained_earnings / total_assets
    #C = earnings before interest and tax / total assets
    c_ = ebit / total_assets
    #D = market value of equity / total liabilities
    current_stock_price = si.get_live_price(ticker)
    market_value_equity = current_stock_price * shs_out
    d_ = market_value_equity / total_liabilities
    #E = sales / total assets
    e_ = sales / total_assets

    z_score = (1.2*a_) + (1.4*b_) + (3.3*c_) + (0.6*d_) + (1.0*e_)

    return z_score


def health_rating(z_score, stock, quick_ratio, current_ratio, debt_eq, debt_eq_industry_average,
                  current_ratio_industry_average):
    health_rating = 0
    if quick_ratio == QUICK_RATIO_MIDDLE:
        health_rating += 1
    elif 1.5 >= quick_ratio > QUICK_RATIO_MIDDLE:
        health_rating += 2
    elif .90 <= quick_ratio < QUICK_RATIO_MIDDLE:
        health_rating -= 1
    elif quick_ratio > 1.5:
        health_rating += 3
    elif .80 <= quick_ratio < .90:
        health_rating -= 2
    elif quick_ratio < .80:
        health_rating -= 3

    if z_score >= GOOD_Z:
        health_rating += 2
    elif 2.7 <= z_score < GOOD_Z:
        health_rating += 1
    elif BAD_Z < z_score < 2.7:
        health_rating -= 1
    elif z_score <= BAD_Z:
        health_rating -= 2

    if current_ratio == 1:
        health_rating += 0
    elif 1.5 <= current_ratio <= 3.0:
        health_rating += 2.5
    elif 1.0 < current_ratio < 1.5:
        health_rating += 1
    elif .9 <= current_ratio < 1.0:
        health_rating -= 1
    elif current_ratio < .9:
        health_rating -= 2.5
    if current_ratio < (current_ratio_industry_average - .1) or current_ratio < (current_ratio + .1):
        health_rating -= 1
    elif current_ratio > (current_ratio_industry_average - .1) or current_ratio > current_ratio < (current_ratio + .1):
        health_rating += 1
    if debt_eq > debt_eq_industry_average:
        health_rating -= 1.5
    elif debt_eq < debt_eq_industry_average:
        health_rating += 1.5

    if health_rating < 0:
        health_rating = 0
    # less than 1 is bad for quick and more than 1 is good
    # z score close to 1.8 bad close to 3.0 good
    # between 1.5 to 3 is good current, under one bad, above 3 also bad because inefficient use of resources
    # debt/eq .3 to .6 good
    return health_rating, quick_ratio, current_ratio, debt_eq, debt_eq_industry_average, \
           current_ratio_industry_average


def industry_values(ticker):
    bruh = True
    # if now == "9:30:00" or now == "10:30:00" or now == "11:30:00":
    if bruh == True:
        link = "https://finviz.com/quote.ashx?t=" + ticker
        contents = requests.get(link).text
        soup = bs(contents, 'lxml')
        line = soup.find(class_="fullview-title")
        p = line.find(class_="fullview-links")
        s = p.find(class_="tab-link")
        r = s.find_next(class_="tab-link")
        for d in r:
            industry = d
            break
        industry = industry.replace(" ", "")
        industry = industry.replace("&", "")
        industry = industry.replace("-", "")
        industry = industry.replace("/", "")
        industry = industry.lower()
        companies = []
        page_number = str(0)
        link = "https://finviz.com/screener.ashx?v=111&f=ind_" + industry + "&r=" + page_number
        contents = requests.get(link).text
        soup = bs(contents, 'lxml')
        dude = soup.findAll(class_="screener-link-primary")

        for i in range(len(dude)):
            for j in dude[i]:
                companies.append(j)
        page_number = str(21)
        while companies[-1] != companies[-2]:
            link = "https://finviz.com/screener.ashx?v=111&f=ind_" + industry + "&r=" + page_number
            contents = requests.get(link).text
            soup = bs(contents, 'lxml')
            dude = soup.findAll(class_="screener-link-primary")

            for i in range(len(dude)):
                for j in dude[i]:
                    companies.append(j)
                page_number = int(page_number)
                page_number += 20
                page_number = str(page_number)
        companies.remove(companies[-1])
        roas = []
        pes = []
        roes = []
        pmargins = []
        pbs = []
        des = []
        crs = []
        indicators = ["ROA", "P/E", "ROE", "Profit Margin", "P/B", "Debt/Eq", "Current Ratio"]
        all_values = []
        for company in companies:
            link = "https://finviz.com/quote.ashx?t=" + company
            contents = requests.get(link).text
            soup = bs(contents, 'lxml')
            for i in range(len(indicators)):
                line = soup.find(text=indicators[i])
                value = line.find_next(class_='snapshot-td2').text
                all_values.append(value)
                convert_value(all_values)
                if indicators[i] == "ROA":
                    roas.append(all_values[-1])
                elif indicators[i] == "P/E":
                    pes.append(all_values[-1])
                elif indicators[i] == "ROE":
                    roes.append(all_values[-1])
                elif indicators[i] == "Profit Margin":
                    pmargins.append(all_values[-1])
                elif indicators[i] == "P/B":
                    pbs.append(all_values[-1])
                elif indicators[i] == "Debt/Eq":
                    des.append(all_values[-1])
                elif indicators[i] == "Current Ratio":
                    crs.append(all_values[-1])
        average_roa = sum(roas) / (len(companies))
        average_pe = sum(pes) / (len(companies))
        average_roe = sum(roes) / len(companies)
        average_p_margin = sum(pmargins) / len(companies)
        average_pb = sum(pbs) / len(companies)
        average_de = sum(des) / len(companies)
        average_cr = sum(crs) / len(companies)
    return average_roa, average_pe, average_roe, average_p_margin, average_pb, average_de, average_cr, roas, roes, \
           pmargins


def news(ticker):
    link = "https://finviz.com/quote.ashx?t=" + ticker + "&ty=c&ta=1&p=d"
    contents = requests.get(link).text
    soup = bs(contents, 'lxml')
    lines = soup.findAll(class_="tab-link-news")
    table = soup.find(class_="fullview-news-outer")
    dates = table.findAll(width="130")
    date_list = []
    links = []
    summary_list = []
    for date in dates:
        string = str(date).replace("<td align=\"right\" style=\"white-space:nowrap\" width=\"130\">", "")
        string = string.replace("<td align=\"right\" width=\"130\">", "")
        string = string.replace("</td>", "")
        string = string.replace(u'\xa0', u'')
        date_list.append(str(string))

    for line in lines:
        line = str(line)[31::]
        for i in range(len(line)):
            if line[i] == "." and line[i + 1] == "h" and line[i + 2] == "t":
                cut_off = (i + 5)
            if line[i] == "=" and line[i + 1] == "y" and line[i + 2] == "a":
                cut_off = (i + 6)
        link = line[:cut_off:]
        links.append(link)
        summary = line[cut_off::]
        summary = summary.replace("\" target=\"_blank\">", "")
        summary = summary.replace("</a>", "")
        summary_list.append(summary)
    return date_list, links, summary_list


def profitability_rating(roa, roe, profit_margin, industry_roa, industry_roe, industry_pm, roa_list, roe_list, pm_list):
    roa_list.sort()
    roe_list.sort()
    pm_list.sort()

    for i in range(len(roa_list)):
        if roa_list[i] == roa:
            place_holder_roa = i
    percent_roa = (place_holder_roa / len(roa_list)) * 100

    for i in range(len(roe_list)):
        if roe_list[i] == roe:
            place_holder_roe = i
    percent_roe = (place_holder_roe / len(roe_list)) * 100

    for i in range(len(pm_list)):
        if pm_list[i] == profit_margin:
            place_holder_pm = i
    percent_pm = (place_holder_pm / len(pm_list)) * 100

    rating_roa = int(str(percent_roa)[0:1])
    rating_roe = int(str(percent_roe)[0:1])
    rating_pm = int(str(percent_pm)[0:1])

    returned_roa = str(percent_roa)[0:4] + "%"
    returned_roe = str(percent_roe)[0:4] + "%"
    returned_pm = str(percent_pm)[0:4] + "%"

    profitability_rating = (rating_roa + rating_roe + rating_pm) / 3

    if profitability_rating > 10:
        profitability_rating = 10

    if float(str(profitability_rating)[1::]) >= .65:
        difference_one = 1 - float(str(profitability_rating)[1::])
        profitability_rating += difference_one
    elif float(str(profitability_rating)[1::]) <= .35:
        difference_two = float(str(profitability_rating)[1::])
        profitability_rating -= difference_two

    return profitability_rating, returned_roa, returned_roe, returned_pm


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.layout = html.Div(children=[
    html.H3(children="Stock Analysis"),

    html.Label("Enter ticker"),
    dcc.Input(
        id='dropdown',
        placeholder="Enter valid ticker",
        type="text",
        value=""

    ),
    html.Div(id='output'),

    dcc.Graph(
        id='example-graph',
        figure={
            'data': [
                {'x': [1, 2, 3], 'y': [4, 1, 2], 'type': 'bar', 'name': 'SF'},
                {'x': [1, 2, 3], 'y': [2, 4, 5], 'type': 'bar', 'name': u'Montréal'},
            ],
            'layout': {
                'title': 'Dash Data Visualization'
            }
        }
    )
])


@app.callback(Output('output', 'children'),
              [Input('dropdown', 'value')])
def check_stock(input_value):
    my_variable = input_value
    stock = yf.Ticker(my_variable)
    flag = True
    #return 'You\'ve entered "{}"'.format(bruh.info)
    try:
        stock.info
    except KeyError:
        return "Invalid Ticker"
        flag = False
    except AssertionError:
        return "Invalid Ticker"
        flag = False


if __name__ == "__main__":
    ticker = get_stock()
    while check_if_stock_is_valid(ticker) is False:
        ticker = get_stock()
    stock = yf.Ticker(ticker)
    information, quarterly_financials, quarterly_balance_sheet = get_basic_info(stock)

    recent_quarter_total_assets, net_income_ttm, total_liabilities, retained_earnings, \
        current_tot_liab, current_tot_assets, ebit = qb_qf_values(quarterly_balance_sheet, quarterly_financials)

    date = get_todays_date()
    values_list = scrape_finviz(ticker)
    modified_values = convert_value(values_list)
    dividend_rating, dividend_yield, increases, decreases, constants, five_annual_changes = \
        dividend_rating(stock, ticker, date, modified_values[7])
    number_of_ratings, sell_count, buy_count, hold_count, firms, dates = analyst_recommendations(stock, ticker, date)
    ins_own, ins_trans, inst_own, inst_trans = institutional_values(stock, modified_values[19], modified_values[20],
                                                                    modified_values[21], modified_values[22])

    average_roa, average_pe, average_roe, average_p_margin, average_pb, average_de, average_cr, roa_list, roe_list, \
        pm_list = industry_values(ticker)

    growth_rating, eps_ttm, eps_next_y, eps_next_q, eps_this_y, eps_next_five_y, eps_past_five_y, \
        four_year_revenue_change, four_quarter_revenue_change, eps_next_y_percent = \
        growth_rating(stock, modified_values[13], modified_values[14], modified_values[15],
                      modified_values[16], modified_values[17], modified_values[18], modified_values[-1])

    z_score = calculate_z_score(net_income_ttm, modified_values[24], modified_values[23], retained_earnings,
                                current_tot_liab, current_tot_assets, recent_quarter_total_assets, total_liabilities,
                                ebit)

    health_rating, quick_ratio, current_ratio, debt_eq, debt_eq_industry_average, current_ratio_industry_average = \
        health_rating(z_score, stock, modified_values[2], modified_values[3], modified_values[4], average_de, average_cr)

    profitability_rating, industry_perf_roa, industry_perf_roe, industry_perf_pm = \
        profitability_rating(modified_values[25], modified_values[26], modified_values[27], average_roa, average_roe,
                             average_p_margin, roa_list, roe_list, pm_list, )

    news_dates, news_links, news_summary = news(ticker)

    print("Ticker:", ticker.upper())
    print("***********")
    print("Dividend Yield:", dividend_yield)
    print("Dividend Rating:", dividend_rating)
    if increases >= 1:
        print("Annual dividend increased", increases, "years in a row")
    elif decreases >= 1:
        print("Annual dividend decreased", decreases, "years in a row")
    elif constants >= 1:
        print("Annual dividend remained constant", constants, "years in a row")
    if dividend_yield > 0:
        if five_annual_changes > 0:
            print("On average, annual dividend increased each year by", str(five_annual_changes)[:4] + "%",
              "over the past 5 years")
        elif five_annual_changes < 0:
            print("On average, annual dividend decreased each year by", str(five_annual_changes)[:4] + "%",
              "over the past 5 years")
        elif five_annual_changes == 0:
            print("Annual dividend remained constant")
    print("***********")
    if number_of_ratings != 0:
        print("Analyst Ratings:\n- Buy:", str(buy_count) + "/" + str(number_of_ratings), "-",
              str(((buy_count / number_of_ratings) * 100))[:5] + "%")
        print("- Hold:", str(hold_count) + "/" + str(number_of_ratings), "-",
              str(((hold_count / number_of_ratings) * 100))[:5] + "%")
        print("- Sell:", str(sell_count) + "/" + str(number_of_ratings), "-",
              str(((sell_count / number_of_ratings) * 100))[:5] + "%")
    else:
        print("No analyst recommendations in", date.year)
    print("***********")
    print("Insider Ownership: ", str(ins_own) + "%")
    print("6 month change in insider ownership", str(ins_trans) + "%")
    print("Institutional Ownership: ", str(inst_own) + "%")
    print("3 month change in institutional ownership", str(inst_trans) + "%")
    print("***********")
    # calculate risk rating
    print("beta is", information["beta"])
    print("***********")
    print("Growth Rating: ", growth_rating)
    print("EPS (ttm): ", eps_ttm)
    print("EPS next quarter: ", eps_next_q)
    print("EPS this year: ", str(eps_this_y) + "%")
    print("EPS next year: ", str(eps_next_y))
    print("EPS past five years: ", str(eps_past_five_y) + "%")
    print("EPS next five years: ", str(eps_next_five_y) + "%")
    print("Four year revenue change: ", str(four_year_revenue_change) + "%")
    print("Four quarter revenue change: ", str(four_quarter_revenue_change) + "%")
    print("***********")
    print("Health rating: ", health_rating)
    print("Z-Score: ", z_score)
    print("Quick Ratio: ", quick_ratio)
    print("Current Ratio: ", current_ratio)
    print("Debt/Equity: ", debt_eq)
    if current_ratio < (current_ratio_industry_average - .1) or current_ratio < (current_ratio + .1):
        print("Current Ratio is less than the industry current ratio of", current_ratio_industry_average)
    elif current_ratio > (current_ratio_industry_average - .1) or current_ratio > current_ratio < (current_ratio + .1):
        print("Current Ratio is greater than the industry current ratio of", current_ratio_industry_average)
    if debt_eq > debt_eq_industry_average:
        print("Debt/Eq is greater than the industry current ratio of", debt_eq_industry_average)
    elif debt_eq < debt_eq_industry_average:
        print("Debt/Eq is less than the industry current ratio of", debt_eq_industry_average)
    print("***********")
    print("Profitability rating: ", profitability_rating)
    if modified_values[25] > (average_roa + .5):
        print(ticker.upper(), "has a Return on Assets of", str(modified_values[25]) + "%.",
              "This is better than the industry average of", str(average_roa) + "%.", ticker.upper(),
              "Outperforms its industry by", str(industry_perf_roa) + "%.")
    elif modified_values[25] < (average_roa - .5):
        print(ticker.upper(), "has a Return on Assets of", str(modified_values[25]) + "%.",
              "This is worse than the industry average of", str(average_roa) + "%.", ticker.upper(),
              "Underperforms its industry by", str(industry_perf_roa) + "%.")
    elif (average_roa + .5) >= modified_values[25] <= (average_roa - .5):
        print(ticker.upper(), "has a Return on Assets of", str(modified_values[25]) + "%.",
              "This is in line with the industry average of", str(average_roa) + "%.", ticker.upper(),
              "performance is in the middle of its industry with", str(industry_perf_roa) + "%.")

    if modified_values[26] > (average_roe + .5):
        print(ticker.upper(), "has a Return on Equity of", str(modified_values[26]) + "%.",
              "This is better than the industry average of", str(average_roe) + "%.", ticker.upper(),
              "Outperforms its industry by", str(industry_perf_roe) + "%.")
    elif modified_values[26] < (average_roe - .5):
        print(ticker.upper(), "has a Return on Equity of", str(modified_values[26]) + "%.",
              "This is worse than the industry average of", str(average_roe) + "%.", ticker.upper(),
              "Underperforms its industry by", str(industry_perf_roe) + "%.")
    elif (average_roe + .5) >= modified_values[26] <= (average_roe - .5):
        print(ticker.upper(), "has a Return on Equity of", str(modified_values[26]) + "%.",
              "This is in line with the industry average of", str(average_roe) + "%.", ticker.upper(),
              "performance is in the middle of its industry with", str(industry_perf_roe) + "%.")

    if modified_values[27] > (average_p_margin + .5):
        print(ticker.upper(), "has a Profit Margin of", str(modified_values[27]) + "%.",
              "This is better than the industry average of", str(average_p_margin) + "%.", ticker.upper(),
              "Outperforms its industry by", str(industry_perf_pm) + "%.")
    elif modified_values[27] < (average_p_margin - .5):
        print(ticker.upper(), "has a Profit Margin of", str(modified_values[27]) + "%.",
              "This is worse than the industry average of", str(average_p_margin) + "%.", ticker.upper(),
              "Underperforms its industry by", str(industry_perf_pm) + "%.")
    elif (average_p_margin + .5) >= modified_values[27] <= (average_p_margin - .5):
        print(ticker.upper(), "has a Profit Margin of", str(modified_values[27]) + "%.",
              "This is in line with the industry average of", str(average_p_margin) + "%.", ticker.upper(),
              "performance is in the middle of its industry with", str(industry_perf_pm) + "%.")
    print("***********")
    data = {"Title": news_summary, "Link": news_links}
    news_table = pd.DataFrame(data, columns=["Title", "Link"])
    news_table = pd.DataFrame(data, index=[news_dates])
    #with pd.option_context('display.max_rows', None, 'display.max_columns', None):
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', -1)
    print(news_table)
    app.run_server(debug=True)

    import dash
    import dash_core_components as dcc
    import dash_html_components as html
    from dash.dependencies import Input, Output, State
    import dash_daq as daq
    import pandas as pd
    import numpy as np
    import urllib as u
    from bs4 import BeautifulSoup as bs
    import requests
    import yfinance as yf
    from yahoo_fin import stock_info as si
    import datetime
    import time
    import os
    import redis
    from flask_caching import Cache
    from Main import qb_qf_values, scrape_finviz, convert_value, get_todays_date, dividend_rating_function, \
        calculate_z_score, industry_values, profitability_rating_function, institutional_values, growth_rating_function, \
        health_rating_function

    MOST_RECENT_QUARTER = 4

    timeout = 20
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
    cache = Cache(app.server, config={
        # try 'filesystem' if you don't want to setup redis
        'CACHE_TYPE': 'redis',
        'CACHE_REDIS_URL': os.environ.get('REDIS_URL', '')
    })
    app.config.suppress_callback_exceptions = True

    app.layout = html.Div(children=[
        html.H3(
            id="title",
            children="Stock Analysis",
        ),
        html.Div(children='30 second delay'),
        html.Div(children="If nothing appears click outside the box then re-click box and hit enter once more"),
        html.Div(children="Will take approximately one minute for everything to load"),

        html.Label("Enter ticker"),
        dcc.Input(
            id='input_box',
            placeholder="Enter valid ticker",
            type="text",
            debounce=True,
        ),
        html.Button(id='submit-button', n_clicks_timestamp=-1, children='Submit', style={'display': 'inline-block'}),

        html.Div(id='output'),
        html.Div(id='bruh'),
        html.Div(children='Number above must change after entering the first ticker'),
        daq.Gauge(
            id="profit-gauge",
            color={"gradient": True, "ranges": {"red": [0, 3], "yellow": [3, 7], "green": [7, 10]}},
            label="Profitability Rating",
            max=10,
            min=0,
        ),
        daq.Gauge(
            id="dividend-gauge",
            color={"gradient": True, "ranges": {"red": [0, 3], "yellow": [3, 7], "green": [7, 10]}},
            label="Dividend Rating",
            max=10,
            min=0,
        ),
        daq.Gauge(
            id="growth-gauge",
            color={"gradient": True, "ranges": {"red": [0, 3], "yellow": [3, 7], "green": [7, 10]}},
            label="Growth Rating",
            max=10,
            min=0,
        ),
        daq.Gauge(
            id="health-gauge",
            color={"gradient": True, "ranges": {"red": [0, 3], "yellow": [3, 7], "green": [7, 10]}},
            label="Health Rating",
            max=10,
            min=0,
        ),
        dcc.Graph(
            id='example-graph',
            figure={
                'data': [
                    {'x': [1, 2, 3], 'y': [4, 1, 2], 'type': 'bar', 'name': 'SF'},
                    {'x': [1, 2, 3], 'y': [2, 4, 5], 'type': 'bar', 'name': u'Montréal'},
                ],
                'layout': {
                    'title': 'Dash Data Visualization'
                }
            }
        )

    ])


    @app.callback(Output('output', 'children'),
                  [Input('submit-button', 'n_clicks_timestamp')],
                  [State('input_box', 'value')])
    def do_everything(n_clicks_timestamp, user_input):
        print("stock")
        global ticker, stock
        print(user_input)

        ticker = str(user_input)
        stock = yf.Ticker(ticker)
        try:
            stock.info

        except KeyError:
            return "Invalid Ticker"
        except AssertionError:
            return "Invalid Ticker"


    @app.callback(Output('profit-gauge', 'value'), [Input('input_box', 'value')])
    def populate_pg(user_input):
        global recent_quarter_total_assets, net_income_ttm, total_liabilities, retained_earnings, current_tot_liab, \
            current_tot_assets, ebit, industry_perf_pm, industry_perf_roe, industry_perf_roa, modified_values, average_roa, \
            average_pe, average_roe, average_p_margin, average_pb, average_de, average_cr, roa_list, \
            roe_list, pm_list
        print("pg")
        # time.sleep(20)

        recent_quarter_total_assets, net_income_ttm, total_liabilities, retained_earnings, \
        current_tot_liab, current_tot_assets, ebit = qb_qf_values(stock)
        print(current_tot_assets)
        values_list = scrape_finviz(ticker)
        print(values_list)

        modified_values = convert_value(values_list)
        print(modified_values)

        average_roa, average_pe, average_roe, average_p_margin, average_pb, average_de, average_cr, roa_list, roe_list, \
        pm_list = industry_values(ticker)
        print(pm_list)

        profitability_rating, industry_perf_roa, industry_perf_roe, industry_perf_pm = \
            profitability_rating_function(modified_values[25], modified_values[26], modified_values[27], average_roa,
                                          average_roe,
                                          average_p_margin, roa_list, roe_list, pm_list)
        print(profitability_rating)
        return profitability_rating


    @app.callback(Output('bruh', 'children'), [Input('input_box', 'value')])
    def bruh_s(user_input):
        print("b")
        print(ebit)
        return ebit


    @app.callback(Output('dividend-gauge', 'value'), [Input('input_box', 'value')])
    def populate_dr(user_input):
        print("dr")
        now = get_todays_date()
        global dividend_rating, dividend_yield, increases, decreases, constants, five_annual_changes
        dividend_rating, dividend_yield, increases, decreases, constants, five_annual_changes = \
            dividend_rating_function(stock, ticker, now, modified_values[7])
        print(dividend_rating)
        return dividend_rating


    @app.callback(Output('health-gauge', 'value'), [Input('input_box', 'value')])
    def populate_h(user_input):
        print("h")
        z_score = calculate_z_score(ticker, modified_values[24], modified_values[23], retained_earnings,
                                    current_tot_liab, current_tot_assets, recent_quarter_total_assets,
                                    total_liabilities,
                                    ebit)
        global health_rating, quick_ratio, current_ratio, debt_eq, debt_eq_industry_average, current_ratio_industry_average
        health_rating, quick_ratio, current_ratio, debt_eq, debt_eq_industry_average, current_ratio_industry_average = \
            health_rating_function(z_score, stock, modified_values[2], modified_values[3], modified_values[4],
                                   average_de,
                                   average_cr)
        print(health_rating)
        return health_rating


    @app.callback(Output('growth-gauge', 'value'), [Input('input_box', 'value')])
    def populate_g(user_input):
        print("g")
        global growth_rating, eps_ttm, eps_next_y, eps_next_q, eps_this_y, eps_next_five_y, eps_past_five_y, \
            four_year_revenue_change, four_quarter_revenue_change, eps_next_y_percent
        growth_rating, eps_ttm, eps_next_y, eps_next_q, eps_this_y, eps_next_five_y, eps_past_five_y, \
        four_year_revenue_change, four_quarter_revenue_change, eps_next_y_percent = \
            growth_rating_function(stock, modified_values[13], modified_values[14], modified_values[15],
                                   modified_values[16], modified_values[17], modified_values[18], modified_values[-1])
        print(growth_rating)
        return growth_rating


    if __name__ == "__main__":
        app.run_server(debug=True)
