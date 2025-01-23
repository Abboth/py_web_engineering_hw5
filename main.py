import logging
import aiohttp
import asyncio
import sys
import datetime
import platform
from time import time
from prettytable import PrettyTable


class HttpError(Exception):
    pass


async def fetch_data(url: str, session):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise HttpError(f"HTTP error: {response.status}")
    except aiohttp.ClientError as e:
        raise HttpError(f"Connection error {url}: {e}")


async def gather_all_fetches(days: int):
    today = datetime.date.today()
    get_urls = [
        (f"https://api.privatbank.ua/p24api/exchange_rates?json&date="
         f"{(today - datetime.timedelta(days=i + 1)).strftime('%d.%m.%Y')}")
        for i in range(days)
    ]
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_data(url, session) for url in get_urls]
        return await asyncio.gather(*tasks)


async def parse_data(data):
    parsed_data = {}
    for day in data:
        date = day["date"]
        exchange_rate = [item for item in day["exchangeRate"] if item["currency"] in ["USD", "EUR", "PLN"]]
        parsed_data[date] = exchange_rate
    return parsed_data


async def get_chosen_currency(data, currency: str):
    filtered_data = {}
    for day in data:
        date = day["date"]
        exchange_rate = [
            item for item in day["exchangeRate"]
            if item["currency"] == currency.upper()
        ]
        if exchange_rate:
            filtered_data[date] = exchange_rate
        else:
            raise ValueError(f"No exchange rate found for currency {currency} on {date}")
    return filtered_data


async def pretty_view(data):
    for date, currency in data.items():
        print(f"Exchange rates for {date}:")
        table = PrettyTable()
        table.field_names = ["Currency", "Sale Rate", "Purchase Rate"]
        for item in currency:
            table.add_row([item["currency"], item["saleRate"], item["purchaseRate"]])
        return table


async def main(args):
    if len(args) < 2:
        logging.error("Please provide at least one argument -> days and optionally currency.")
        return

    try:
        if int(args[1]) < 10:
            days = int(args[1])
        else:
            raise ValueError
    except ValueError:
        logging.error("Invalid number of days. Please provide integer value between 1-10.")
        return

    currency = args[2] if len(args) == 3 else None

    try:
        raw_data = await gather_all_fetches(days)
        logging.info(f"Data for {days} fetched")
        parsed_data = await parse_data(raw_data)

        if currency:
            chosen_currency = await get_chosen_currency(raw_data, currency)
            return await pretty_view(chosen_currency)
        else:
            return await pretty_view(parsed_data)

    except HttpError as e:
        logging.error(f"Error: {e}")
    except ValueError as e:
        logging.error(f"Error: {e}")


if __name__ == "__main__":
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    time_start = time()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main(sys.argv))
    print(f"Execution time: {time() - time_start:.2f} seconds")
