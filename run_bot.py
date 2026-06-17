"""
BTC Market Making Bot — Binance Testnet

Setup:
  1. Go to https://testnet.binance.vision and log in with GitHub
  2. Generate API key + secret, copy into .env
  3. pip install -r requirements.txt
  4. python run_bot.py

Controls:
  Ctrl+C to stop — open orders are cancelled on exit.
"""

import asyncio
import os
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

import config
from bot.exchange import BinanceTestnet
from bot.feed import BookTicker
from bot.strategy import ASStrategy
from bot.tracker import PositionTracker

_NETWORK_EXC = (requests.exceptions.ConnectionError, requests.exceptions.Timeout)
_OFFLINE_RETRY = 60   # 全部重试耗尽后，等这么多秒再恢复报价

load_dotenv()

API_KEY    = os.getenv("BINANCE_TESTNET_API_KEY", "")
API_SECRET = os.getenv("BINANCE_TESTNET_SECRET", "")


async def main() -> None:
    if not API_KEY or not API_SECRET:
        print("ERROR: set BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_SECRET in .env")
        return

    # ── Setup ──────────────────────────────────────────────────────────
    exchange = BinanceTestnet(API_KEY, API_SECRET)
    feed     = BookTicker(config.SYMBOL)
    strategy = ASStrategy(
        gamma=config.GAMMA,
        delta_0=config.DELTA_0,
        delta_min=config.DELTA_MIN,
    )

    # Get starting balances from testnet
    balances    = exchange.get_balances()
    initial_usdt = balances.get("USDT", 0.0)
    initial_btc  = balances.get("BTC", 0.0)
    print(f"[init] USDT={initial_usdt:,.2f}  BTC={initial_btc:.4f}")

    log_name = f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    tracker  = PositionTracker(
        initial_cash=initial_usdt,
        initial_inventory=0.0,
        log_path=log_name,
    )
    print(f"[bot] logging to {log_name}")

    # Active order IDs: {"bid": id, "ask": id}
    active_orders: dict = {}
    last_log_time = 0.0

    # ── Quote loop ─────────────────────────────────────────────────────
    async def quote_loop() -> None:
        nonlocal active_orders, last_log_time

        await asyncio.sleep(1)   # let feed warm up

        while True:
            try:
                mid = feed.mid
                if mid is None:
                    await asyncio.sleep(1)
                    continue

                # 1. Check which active orders got filled
                open_ids = {o["orderId"] for o in exchange.get_open_orders(config.SYMBOL)}
                for label, oid in list(active_orders.items()):
                    if oid not in open_ids:
                        order = exchange.get_order(config.SYMBOL, oid)
                        if order.get("status") == "FILLED":
                            side = order["side"]
                            price = float(order["price"])
                            qty   = float(order["executedQty"])
                            tracker.record_fill(side, price, qty)
                        active_orders.pop(label, None)

                # 2. Hard inventory limit — skip requote if limit breached
                inv = tracker.inventory
                if abs(inv) >= config.MAX_INVENTORY:
                    print(f"  [limit] inventory {inv:+.4f} BTC at hard cap, skipping quote")
                    await asyncio.sleep(config.QUOTE_INTERVAL)
                    continue

                # 3. Cancel remaining open orders
                if active_orders:
                    exchange.cancel_all_orders(config.SYMBOL)
                    active_orders.clear()

                # 4. Compute new quotes via AS strategy
                bid_px, ask_px = strategy.get_quotes(mid, inv)
                bid_px = round(bid_px, 2)
                ask_px = round(ask_px, 2)

                # 5. Place new orders
                try:
                    bid_order = exchange.place_limit_order(
                        config.SYMBOL, "BUY", bid_px, config.LOT_SIZE)
                    active_orders["bid"] = bid_order["orderId"]
                except Exception as e:
                    print(f"  [warn] bid order failed: {e}")

                try:
                    ask_order = exchange.place_limit_order(
                        config.SYMBOL, "SELL", ask_px, config.LOT_SIZE)
                    active_orders["ask"] = ask_order["orderId"]
                except Exception as e:
                    print(f"  [warn] ask order failed: {e}")

                # 6. Log quote to CSV
                tracker.log_quote(mid, bid_px, ask_px)

                # 7. Periodic P&L log
                now = time.time()
                if now - last_log_time >= config.LOG_INTERVAL:
                    ts  = datetime.now(timezone.utc).strftime("%H:%M:%S")
                    tau = strategy.current_tau()
                    print(f"[{ts}] mid=${mid:,.2f}  bid=${bid_px:,.2f}  ask=${ask_px:,.2f}  "
                          f"τ={tau:.2f}  {tracker.summary(mid)}")
                    last_log_time = now

                await asyncio.sleep(config.QUOTE_INTERVAL)

            except _NETWORK_EXC as e:
                # exchange.py 三次重试全部失败 → 彻底断网，等待恢复
                print(f"  [offline] 网络断开 ({e.__class__.__name__})，"
                      f"暂停报价 {_OFFLINE_RETRY}s，open orders 状态未知")
                active_orders.clear()   # 不知道订单状态，清空本地记录
                await asyncio.sleep(_OFFLINE_RETRY)

    # ── Run ────────────────────────────────────────────────────────────
    print(f"[bot] starting  symbol={config.SYMBOL}  "
          f"lot={config.LOT_SIZE} BTC  interval={config.QUOTE_INTERVAL}s")
    print("[bot] press Ctrl+C to stop\n")

    try:
        await asyncio.gather(feed.run(), quote_loop())
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        print("\n[bot] shutting down — cancelling open orders…")
        exchange.cancel_all_orders(config.SYMBOL)
        mid = feed.mid or 0
        tracker.print_report(mid)


if __name__ == "__main__":
    asyncio.run(main())
