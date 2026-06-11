CREATE TABLE instruments (
  id SERIAL PRIMARY KEY,
  type VARCHAR(100) NOT NULL,
  brand VARCHAR(100) NOT NULL,
  serial_no VARCHAR(100) UNIQUE NOT NULL,
  condition VARCHAR(50) NOT NULL CHECK (condition IN ('Excellent', 'Good', 'Fair')),
  status VARCHAR(50) NOT NULL DEFAULT 'Available' CHECK (
    status IN ('Available', 'On Loan', 'Under Repair')
  ),
  notes TEXT DEFAULT '',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE loans (
  id SERIAL PRIMARY KEY,
  instrument_id INTEGER NOT NULL REFERENCES instruments(id),
  student_name VARCHAR(150) NOT NULL,
  student_phone VARCHAR(20) NOT NULL,
  loan_date DATE NOT NULL,
  expected_return_date DATE NOT NULL,
  deposit_collected DECIMAL(10, 2) NOT NULL,
  condition_at_loan TEXT NOT NULL,
  condition_photo_url VARCHAR(500) DEFAULT '',
  is_returned BOOLEAN DEFAULT FALSE,
  return_date DATE,
  condition_at_return TEXT,
  damage_notes TEXT,
  damage_deduction DECIMAL(10, 2) DEFAULT 0.00,
  deposit_refunded DECIMAL(10, 2),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);