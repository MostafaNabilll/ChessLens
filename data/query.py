import duckdb

conn = duckdb.connect('chesslens.duckdb')

while True:
    query = input("sql> ")
    if query.lower() in ('exit', 'quit'):
        break
    try:
        print(conn.execute(query).fetchdf())
    except Exception as e:
        print(e)