# Reports Module API Documentation

## Overview
The reports module provides comprehensive analytics and reporting functionality for the RDFS system.

## Endpoints

### 1. Deposit Analytics
**URL:** `/reports/deposit-analytics/`  
**Method:** GET  
**Authentication:** Required (Admin only)  
**Description:** Returns 7-day deposit trends and top vehicles by deposit amount.

**Response:**
```json
{
  "labels": ["Nov 18", "Nov 19", "Nov 20", ...],
  "daily_totals": [1500.00, 2300.00, 1800.00, ...],
  "total_deposits": 12600.00,
  "top_vehicles": [
    {"wallet__vehicle__license_plate": "ABC-123", "total": 5000.00},
    ...
  ]
}
```

### 2. Deposit vs Revenue Comparison
**URL:** `/reports/deposit-vs-revenue/`  
**Method:** GET  
**Authentication:** Required (Admin only)  
**Parameters:**
- `start_date` (optional): YYYY-MM-DD format
- `end_date` (optional): YYYY-MM-DD format

**Description:** Compares daily deposits against terminal fee revenue.

**Response:**
```json
{
  "chart_labels": ["Nov 18", "Nov 19", ...],
  "deposits_data": [1500.00, 2300.00, ...],
  "revenue_data": [1200.00, 1800.00, ...],
  "start_date": "2025-11-18",
  "end_date": "2025-11-25"
}
```

### 3. Profit Report
**URL:** `/reports/profit-report/`  
**Method:** GET  
**Authentication:** Required (Admin only)  
**Parameters:**
- `start_date` (optional): YYYY-MM-DD format
- `end_date` (optional): YYYY-MM-DD format

**Description:** Visual profit trend analysis with date filtering.

**Response:**
```json
{
  "profits": [...],
  "total": 8500.00,
  "profit_labels": ["Nov 18", "Nov 19", ...],
  "profit_values": [500.00, 750.00, ...]
}
```

## Data Models

### Profit Model
- `amount`: Decimal field for profit amount
- `date_recorded`: DateTime when profit was recorded
- `description`: Optional description of profit source

## Authentication & Permissions
All endpoints require:
- User authentication (`@login_required`)
- Admin role verification (`@user_passes_test(is_admin)`)

## Error Handling
- Invalid date formats return to default 7-day range
- Missing permissions redirect to login page
- Database errors return appropriate error messages

## Usage Examples

### Get deposit analytics
```javascript
fetch('/reports/deposit-analytics/')
  .then(response => response.json())
  .then(data => {
    // Use data.daily_totals for chart
    console.log('Total deposits:', data.total_deposits);
  });
```

### Filter profit report by date range
```javascript
const params = new URLSearchParams({
  start_date: '2025-11-01',
  end_date: '2025-11-30'
});

fetch(`/reports/profit-report/?${params}`)
  .then(response => response.json())
  .then(data => {
    // Process filtered profit data
  });
```