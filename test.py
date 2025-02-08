import pandas as pd

def restructure_data():
    # Read the original CSV file
    df = pd.read_csv('Complete_Reformatted_Broker_Data_JAN25.csv')

    # Convert the date format to a consistent format (YYYY-MM-DD)
    df['Date'] = pd.to_datetime(df['Date'], format='%b-%d-%Y').dt.strftime('%Y-%m-%d')

    # Pivot the data so that each broker has one row, and dates are columns
    df_pivot = df.pivot_table(index='Broker', columns='Date', values='Value', aggfunc='sum', fill_value=0)

    # Reset the index to make 'Broker' a column again
    df_pivot.reset_index(inplace=True)

    # Save the restructured data to a new CSV file
    output_filename = 'Restructured_Broker_Data.csv'
    df_pivot.to_csv(output_filename, index=False)

    print(f"Restructured data saved to {output_filename}")
    print("\nPreview of the restructured data:")
    print(df_pivot.head())

if __name__ == "__main__":
    restructure_data()