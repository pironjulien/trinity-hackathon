import duckdb
import os

DB_PATH = "test_chronos.duckdb"


def test_constraint():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    con = duckdb.connect(DB_PATH)

    print("1. Creating Table and Index...")
    con.execute(
        "CREATE TABLE trades (pair VARCHAR, price DOUBLE, volume DOUBLE, side VARCHAR, timestamp BIGINT)"
    )
    con.execute(
        "CREATE UNIQUE INDEX idx_trades_unique ON trades (pair, timestamp, price, volume, side)"
    )

    print("2. Inserting first row...")
    con.execute("INSERT INTO trades VALUES ('BTC/EUR', 50000.0, 1.0, 'buy', 1000)")

    print("3. Attempting duplicate insert with INSERT OR IGNORE...")
    try:
        con.execute(
            "INSERT OR IGNORE INTO trades VALUES ('BTC/EUR', 50000.0, 1.0, 'buy', 1000)"
        )
        print("   SUCCESS: INSERT OR IGNORE worked (no error raised).")
    except Exception as e:
        print(f"   FAILURE: INSERT OR IGNORE raised exception: {e}")

    print("4. Attempting duplicate insert with ON CONFLICT DO NOTHING...")
    try:
        con.execute(
            "INSERT INTO trades VALUES ('BTC/EUR', 50000.0, 1.0, 'buy', 1000) ON CONFLICT DO NOTHING"
        )
        print("   SUCCESS: ON CONFLICT DO NOTHING worked.")
    except Exception as e:
        print(f"   FAILURE: ON CONFLICT DO NOTHING raised exception: {e}")

    con.close()
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


if __name__ == "__main__":
    test_constraint()
