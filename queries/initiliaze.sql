-- This SQL script initializes the database by creating necessary tables
-- and inserting essential categories for the inventory management system.

-- Create the 'categories' table to store different types of components
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add essential categories
INSERT INTO categories (name) VALUES
('Microcontroller'),
('Sensor'),
('Actuator'),
('Display/Screen'),
('Passive Component'),
('Power/Battery'),
('Prototyping/Cables');

-- Create the 'components' table to store information about each component
CREATE TABLE components (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id INT REFERENCES categories(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL, -- example: ESP32-WROOM-32E, DHT11
    quantity INT NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    datasheet_url TEXT, -- example: https://example.com/datasheet.pdf
    technical_specs JSONB DEFAULT '{}'::jsonb, -- example: {"voltage": "3.3V", "protocol": "I2C"}
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create a trigger function to automatically update the 'updated_at' column whenever a component is updated
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create a trigger that calls the function before any update on the 'components' table
CREATE TRIGGER update_components_modtime
    BEFORE UPDATE ON components
    FOR EACH ROW
    EXECUTE PROCEDURE update_modified_column();

-- Create the 'invoices' table to store information about purchases and their associated PDF files
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_name VARCHAR(100) NOT NULL, -- example: Direnç.net, Robotistan
    invoice_date DATE,
    total_amount DECIMAL(10, 2),
    file_path TEXT, -- example: /invoices/2024-06-01-invoice.pdf
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create the 'invoice_items' table to store individual items from each invoice,
-- including the raw name from the invoice and the cleaned name after AI processing
CREATE TABLE invoice_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID REFERENCES invoices(id) ON DELETE CASCADE,
    raw_name TEXT NOT NULL, -- raw name from the invoice, example: "ESP32 WROOM 32E", "DHT11 Sensor"
    clean_name VARCHAR(255), -- cleaned name after AI processing, example: "ESP32-WROOM-32E", "DHT11"
    quantity INT NOT NULL,
    is_processed BOOLEAN DEFAULT FALSE, -- indicates whether the item has been processed and matched to a component
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);