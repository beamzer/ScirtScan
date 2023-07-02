#!/usr/bin/env python3
import sqlite3
import argparse

# Create argument parser
parser = argparse.ArgumentParser(description='Output the contents of a SQLite database.')
parser.add_argument('database', help='The SQLite database file to open')

# Parse arguments
args = parser.parse_args()

# Connect to the SQLite database
connection = sqlite3.connect(args.database)

# Create a cursor object
cursor = connection.cursor()

# Execute the SQL statement
cursor.execute("SELECT * FROM website_checks")

# Print the column names as a header, separated by semicolons
print(';'.join([column[0] for column in cursor.description]))

# Fetch all rows from the result of the SQL statement
rows = cursor.fetchall()

# Iterate through each row
for row in rows:
    # Print the row, with each field separated by a semicolon
    print(';'.join([str(item) for item in row]))

# Close the connection to the database
connection.close()
