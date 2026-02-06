import sqlite3
import random
from datetime import datetime, timedelta
import os

# Real printer models I use or see often
PRINTERS = [
    "Creality Ender 3 V2", "Bambu Lab X1 Carbon", "Prusa MK4", 
    "AnyCubic Kobra 2", "Qidi X-Max 3", "Elegoo Neptune 4"
]

MATERIALS = ["PLA", "PETG", "ABS", "TPU", "ASA", "Nylon"]

BRANDS = [
    "eSun", "Polymaker", "Prusament", "Bambu Lab", 
    "Hatchbox", "Overture", "Sunlu"
]

CATEGORIES = [
    "Functional Parts", "Miniatures", "Prototypes", 
    "Replacement Parts", "Art/Decor", "Engineering Models"
]

# Some realistic reasons why prints fail
FAILURE_REASONS = [
    "Bed adhesion lost", "Nozzle clog", "Layer shift", 
    "Spaghetti monster", "Power outage", "Filament runout",
    "Heat creep", "Model warping"
]

# Print jobs to generate context
PRINT_MODELS = {
    "Functional Parts": [
        "Headphone Stand", "Cable Organizer", "tool holder", "Wall mount", 
        "Laptop Stand", "Drawer divider", "SD card holder"
    ],
    "Miniatures": [
        "D&D Character", "Space Marine", "Dragon", "Chess Set", 
        "Terrain piece", "Fantasy castle"
    ],
    "Prototypes": [
        "Case V1", "Gear mechanism", "Bracket test", "Hinge prototype",
        "Enclosure design"
    ],
    "Replacement Parts": [
        "Dishwasher wheel", "Knob replacement", "Battery cover", 
        "Vacuum clip", "Fridge handle"
    ],
    "Art/Decor": [
        "Voronoi Vase", "Lithophane", "Geometric Planter", 
        "Articulated Lizard", "Moon Lamp"
    ],
    "Engineering Models": [
        "Planetary Gear", "Engine cutout", "Turbine blade", 
        "Suspension model", "Bridge truss"
    ]
}

def create_db(db_path="data/print_analytics.db"):
    # make sure dir exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Clean slate
    c.execute("DROP TABLE IF EXISTS print_jobs")
    
    # Just one main table for now, keep it simple
    c.execute("""
        CREATE TABLE print_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATETIME,
            model_name TEXT,
            printer_name TEXT,
            material_type TEXT,
            filament_brand TEXT,
            weight_used_grams REAL,
            print_time_hours REAL,
            success_status BOOLEAN,
            failure_reason TEXT,
            layer_height REAL,
            infill_percentage INTEGER,
            nozzle_temp INTEGER,
            bed_temp INTEGER,
            cost_usd REAL,
            project_category TEXT
        )
    """)
    
    conn.commit()
    return conn

def generate_data(conn, num_rows=550):
    c = conn.cursor()
    data = []
    
    print(f"Generating {num_rows} print jobs...")
    
    for i in range(num_rows):
        # Random date within last year
        days_back = random.randint(1, 365)
        print_date = datetime.now() - timedelta(days=days_back)
        
        category = random.choice(CATEGORIES)
        model = random.choice(PRINT_MODELS[category])
        
        # Add some variety to model names
        if random.random() > 0.7:
            model += f" v{random.randint(1,5)}"
            
        printer = random.choice(PRINTERS)
        material = random.choice(MATERIALS)
        brand = random.choice(BRANDS)
        
        # Physicsish logic
        weight = random.uniform(5, 500) # grams
        if category == "Miniatures":
            weight = random.uniform(2, 50)
        
        # Print time roughly correlated to weight but varies by printer speed
        speed_factor = 1.0
        if "Bambu" in printer: speed_factor = 3.0 # fast!
        if "Ender" in printer: speed_factor = 0.8 # slower
        
        # Rough calc: 10g per hour avg on standard speed?
        base_time = weight / 12.0 
        print_time = base_time / speed_factor
        print_time = round(print_time * random.uniform(0.8, 1.2), 2)
        
        # Success rate depends on printer slightly
        fail_chance = 0.15 # base 15% fail rate
        if "Bambu" in printer or "Prusa" in printer:
            fail_chance = 0.05 # better printers
            
        is_fail = random.random() < fail_chance
        success = not is_fail
        
        failure_reason = None
        if is_fail:
            failure_reason = random.choice(FAILURE_REASONS)
            # Failed prints usually take less time (fail midway)
            print_time = print_time * random.uniform(0.1, 0.9)
            weight = weight * random.uniform(0.1, 0.9) # wasted material
            
        # Settings
        layer_h = random.choice([0.1, 0.15, 0.2, 0.24, 0.3])
        if category == "Miniatures": layer_h = 0.1
        
        infill = random.choice([10, 15, 20, 40, 100])
        
        # Temps based on material
        nozzle = 200
        bed = 60
        if material == "PLA":
            nozzle = random.randint(195, 215)
            bed = random.randint(50, 65)
        elif material == "PETG":
            nozzle = random.randint(230, 250)
            bed = random.randint(70, 85)
        elif material == "ABS" or material == "ASA":
            nozzle = random.randint(240, 260)
            bed = random.randint(90, 110)
        elif material == "TPU":
            nozzle = random.randint(210, 230)
            bed = random.randint(40, 60)
            
        # Cost calc (approx $20/kg generic)
        cost_per_g = 0.025 # $25/kg avg
        if brand in ["Prusament", "Bambu Lab"]:
            cost_per_g = 0.035 # premium
            
        cost = round(weight * cost_per_g, 2)
        
        data.append((
            print_date, model, printer, material, brand, 
            round(weight, 2), round(print_time, 2), success, failure_reason,
            layer_h, infill, nozzle, bed, cost, category
        ))
        
    query = """
    INSERT INTO print_jobs (
        date, model_name, printer_name, material_type, filament_brand,
        weight_used_grams, print_time_hours, success_status, failure_reason,
        layer_height, infill_percentage, nozzle_temp, bed_temp, cost_usd, project_category
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    c.executemany(query, data)
    conn.commit()
    print("Done! DB ready.")

if __name__ == "__main__":
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "print_analytics.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = create_db(db_path)
    generate_data(conn)
    conn.close()
