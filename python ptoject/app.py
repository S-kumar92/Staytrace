from flask import Flask, render_template, request, redirect, url_for, flash
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# JSON file paths
TRIPS_FILE = 'trips.json'
EXPENSES_FILE = 'expenses.json'

def load_trips():
    """Load trips from JSON file"""
    if os.path.exists(TRIPS_FILE):
        with open(TRIPS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_trips(trips):
    """Save trips to JSON file"""
    with open(TRIPS_FILE, 'w') as f:
        json.dump(trips, f, indent=2)

def load_expenses():
    """Load expenses from JSON file"""
    if os.path.exists(EXPENSES_FILE):
        with open(EXPENSES_FILE, 'r') as f:
            return json.load(f)
    return []

def save_expenses(expenses):
    """Save expenses to JSON file"""
    with open(EXPENSES_FILE, 'w') as f:
        json.dump(expenses, f, indent=2)

def get_next_id(items):
    """Get next ID for new item"""
    if not items:
        return 1
    return max(item.get('id', 0) for item in items) + 1

def calculate_trip_totals(trip_name):
    """Calculate total expenses and remaining budget for a trip"""
    trips = load_trips()
    expenses = load_expenses()
    
    trip = next((t for t in trips if t['trip_name'] == trip_name), None)
    if not trip:
        return 0, 0, 0
    
    budget = float(trip.get('budget', 0))
    trip_expenses = [e for e in expenses if e.get('trip_name') == trip_name]
    total_spent = sum(float(e.get('amount', 0)) for e in trip_expenses)
    remaining = budget - total_spent
    
    return budget, total_spent, remaining

@app.route('/')
def home():
    """Home page showing all trips with summary"""
    trips = load_trips()
    expenses = load_expenses()
    
    # Calculate totals for each trip
    trip_summaries = []
    for trip in trips:
        budget, total_spent, remaining = calculate_trip_totals(trip['trip_name'])
        trip_summaries.append({
            'trip': trip,
            'budget': budget,
            'total_spent': total_spent,
            'remaining': remaining,
            'is_over_budget': remaining < 0
        })
    
    return render_template('home.html', trip_summaries=trip_summaries)

@app.route('/add_trip')
def add_trip():
    """Display form to add a new trip"""
    return render_template('add_trip.html')

@app.route('/save_trip', methods=['POST'])
def save_trip():
    """Save a new trip"""
    trip_name = request.form.get('trip_name', '').strip()
    destination = request.form.get('destination', '').strip()
    start_date = request.form.get('start_date', '').strip()
    end_date = request.form.get('end_date', '').strip()
    budget = request.form.get('budget', '').strip()
    travel_mode = request.form.get('travel_mode', '').strip()
    
    # Validation
    if not all([trip_name, destination, start_date, end_date, budget, travel_mode]):
        flash('All fields are required!', 'danger')
        return redirect(url_for('add_trip'))
    
    try:
        budget = float(budget)
        if budget < 0:
            raise ValueError
    except ValueError:
        flash('Budget must be a valid positive number!', 'danger')
        return redirect(url_for('add_trip'))
    
    # Check if trip name already exists
    trips = load_trips()
    if any(t['trip_name'] == trip_name for t in trips):
        flash('Trip name already exists! Please choose a different name.', 'danger')
        return redirect(url_for('add_trip'))
    
    # Create new trip
    new_trip = {
        'id': get_next_id(trips),
        'trip_name': trip_name,
        'destination': destination,
        'start_date': start_date,
        'end_date': end_date,
        'budget': budget,
        'travel_mode': travel_mode
    }
    
    trips.append(new_trip)
    save_trips(trips)
    
    flash('Trip added successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/add_expense')
def add_expense():
    """Display form to add a new expense"""
    trips = load_trips()
    if not trips:
        flash('Please add a trip first before adding expenses!', 'warning')
        return redirect(url_for('add_trip'))
    return render_template('add_expense.html', trips=trips)

@app.route('/save_expense', methods=['POST'])
def save_expense():
    """Save a new expense"""
    trip_name = request.form.get('trip_name', '').strip()
    category = request.form.get('category', '').strip()
    amount = request.form.get('amount', '').strip()
    date = request.form.get('date', '').strip()
    note = request.form.get('note', '').strip()
    
    # Validation
    if not all([trip_name, category, amount, date]):
        flash('Trip Name, Category, Amount, and Date are required!', 'danger')
        return redirect(url_for('add_expense'))
    
    try:
        amount = float(amount)
        if amount < 0:
            raise ValueError
    except ValueError:
        flash('Amount must be a valid positive number!', 'danger')
        return redirect(url_for('add_expense'))
    
    # Verify trip exists
    trips = load_trips()
    if not any(t['trip_name'] == trip_name for t in trips):
        flash('Selected trip does not exist!', 'danger')
        return redirect(url_for('add_expense'))
    
    # Create new expense
    expenses = load_expenses()
    new_expense = {
        'id': get_next_id(expenses),
        'trip_name': trip_name,
        'category': category,
        'amount': amount,
        'date': date,
        'note': note
    }
    
    expenses.append(new_expense)
    save_expenses(expenses)
    
    flash('Expense added successfully!', 'success')
    return redirect(url_for('view_expenses'))

@app.route('/view_expenses')
def view_expenses():
    """Display all expenses grouped by trip"""
    trips = load_trips()
    expenses = load_expenses()
    
    # Sort expenses by date (newest first)
    expenses.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    # Group expenses by trip
    trip_expenses = {}
    for expense in expenses:
        trip_name = expense.get('trip_name')
        if trip_name not in trip_expenses:
            trip_expenses[trip_name] = []
        trip_expenses[trip_name].append(expense)
    
    # Calculate totals for each trip
    trip_totals = {}
    for trip in trips:
        budget, total_spent, remaining = calculate_trip_totals(trip['trip_name'])
        trip_totals[trip['trip_name']] = {
            'budget': budget,
            'total_spent': total_spent,
            'remaining': remaining,
            'is_over_budget': remaining < 0
        }
    
    return render_template('view_expenses.html', 
                         trips=trips, 
                         trip_expenses=trip_expenses,
                         trip_totals=trip_totals)

@app.route('/edit_expense/<int:expense_id>')
def edit_expense(expense_id):
    """Display form to edit an expense"""
    expenses = load_expenses()
    expense = next((e for e in expenses if e.get('id') == expense_id), None)
    
    if not expense:
        flash('Expense not found!', 'danger')
        return redirect(url_for('view_expenses'))
    
    trips = load_trips()
    return render_template('edit_expense.html', expense=expense, trips=trips)

@app.route('/update_expense/<int:expense_id>', methods=['POST'])
def update_expense(expense_id):
    """Update an existing expense"""
    expenses = load_expenses()
    expense = next((e for e in expenses if e.get('id') == expense_id), None)
    
    if not expense:
        flash('Expense not found!', 'danger')
        return redirect(url_for('view_expenses'))
    
    trip_name = request.form.get('trip_name', '').strip()
    category = request.form.get('category', '').strip()
    amount = request.form.get('amount', '').strip()
    date = request.form.get('date', '').strip()
    note = request.form.get('note', '').strip()
    
    # Validation
    if not all([trip_name, category, amount, date]):
        flash('Trip Name, Category, Amount, and Date are required!', 'danger')
        return redirect(url_for('edit_expense', expense_id=expense_id))
    
    try:
        amount = float(amount)
        if amount < 0:
            raise ValueError
    except ValueError:
        flash('Amount must be a valid positive number!', 'danger')
        return redirect(url_for('edit_expense', expense_id=expense_id))
    
    # Verify trip exists
    trips = load_trips()
    if not any(t['trip_name'] == trip_name for t in trips):
        flash('Selected trip does not exist!', 'danger')
        return redirect(url_for('edit_expense', expense_id=expense_id))
    
    # Update expense
    expense['trip_name'] = trip_name
    expense['category'] = category
    expense['amount'] = amount
    expense['date'] = date
    expense['note'] = note
    
    save_expenses(expenses)
    
    flash('Expense updated successfully!', 'success')
    return redirect(url_for('view_expenses'))

@app.route('/delete_expense/<int:expense_id>')
def delete_expense(expense_id):
    """Delete an expense"""
    expenses = load_expenses()
    expense = next((e for e in expenses if e.get('id') == expense_id), None)
    
    if not expense:
        flash('Expense not found!', 'danger')
        return redirect(url_for('view_expenses'))
    
    expenses = [e for e in expenses if e.get('id') != expense_id]
    save_expenses(expenses)
    
    flash('Expense deleted successfully!', 'success')
    return redirect(url_for('view_expenses'))

if __name__ == '__main__':
    # Initialize JSON files if they don't exist
    if not os.path.exists(TRIPS_FILE):
        save_trips([])
    if not os.path.exists(EXPENSES_FILE):
        save_expenses([])
    
    app.run(debug=True)

