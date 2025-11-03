# Smart Inventory Optimizer

A web application that helps small businesses optimize their inventory levels by analyzing sales data and providing actionable insights.

## Features

- Upload and process sales data (CSV format)
- Visualize demand trends and inventory levels
- Calculate optimal reorder points and safety stock levels
- Identify potential stockouts and overstock situations
- Generate downloadable reports

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/inventory_optimizer.git
   cd inventory_optimizer
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. Start the development server:
   ```bash
   cd src
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

## Data Format

The application expects CSV files with the following columns:
- `Date` (format: YYYY-MM-DD)
- `Product` (product name or ID)
- `Sold_Units` (number of units sold)
- `Current_Stock` (optional, current stock level)

## Project Structure

```
inventory_optimizer/
├── data/                   # Uploaded data files
│   └── uploads/            # User-uploaded files
├── output/                 # Generated reports and exports
├── src/                    # Source code
│   ├── __init__.py
│   ├── app.py              # Main application
│   ├── data_loader.py      # Data loading and validation
│   ├── demand_engine.py    # Demand forecasting logic
│   └── viz.py             # Visualization utilities
├── templates/              # HTML templates
│   ├── base.html           # Base template
│   ├── dashboard.html      # Main dashboard
│   ├── index.html          # Landing page
│   └── static/             # Static files (CSS, JS, images)
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- Built with [Flask](https://flask.palletsprojects.com/)
- Styled with [Tailwind CSS](https://tailwindcss.com/)
- Icons from [Font Awesome](https://fontawesome.com/)
- Charts powered by [Chart.js](https://www.chartjs.org/)
