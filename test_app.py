from app import app
from models import db, User, DealerProfile, Driver, Order, DriverPass

def test_queries():
    with app.app_context():
        users = User.query.all()
        print(f"Total Users: {len(users)}")
        for u in users:
            print(f" - {u.user_id}: {u.username} ({u.role})")
        
        passes = DriverPass.query.all()
        print(f"\nTotal Driver Passes: {len(passes)}")
        for p in passes:
            print(f" - Pass #{p.pass_id}: Order #{p.order_id}, Driver #{p.driver_id}, Dealer #{p.dealer_id}, Status: {p.pass_status}")
            print(f"   Fetched Client: {p.order.client.name}")
            print(f"   Fetched Material: {p.order.material.name} ({p.order.quantity} {p.order.material.unit})")
            print(f"   Fetched Vehicle: {p.driver.vehicle_number}")

if __name__ == '__main__':
    test_queries()
