from datetime import datetime, date, timedelta
from app import app
from models import db, User, DealerProfile, Driver, Material, DealerStock, Order, DriverPass, Payment, Complaint, Feedback, Review

def seed_database():
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database tables created cleanly.")

        # 1. Admin User
        admin = User(
            username='admin',
            email='admin@quarry.com',
            role='admin',
            name='System Administrator',
            phone='9995551111',
            address='SJCET Palai Campus',
            status='active'
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # 2. Dealer Users & Profiles
        dealer1 = User(
            username='apex_quarry',
            email='apex@quarry.com',
            role='dealer',
            name='Apex Rock & Granite Ltd',
            phone='9847012345',
            address='Quarry Road, Palai, Kottayam',
            status='approved'
        )
        dealer1.set_password('dealer123')
        db.session.add(dealer1)

        dealer2 = User(
            username='valley_stone',
            email='valley@quarry.com',
            role='dealer',
            name='Valley Stone Supplies',
            phone='9847054321',
            address='NH Bypass, Ernakulam',
            status='approved'
        )
        dealer2.set_password('dealer123')
        db.session.add(dealer2)

        dealer3 = User(
            username='highland_quarry',
            email='highland@quarry.com',
            role='dealer',
            name='Highland Aggregates',
            phone='9847099999',
            address='Munnar Highway, Idukki',
            status='pending'
        )
        dealer3.set_password('dealer123')
        db.session.add(dealer3)

        db.session.flush() # Flush to get user_ids

        dp1 = DealerProfile(
            dealer_id=dealer1.user_id,
            company_name='Apex Rock & Granite Quarry',
            license_no='QRL-2024-001',
            quarry_location='Palai, Kottayam'
        )
        dp2 = DealerProfile(
            dealer_id=dealer2.user_id,
            company_name='Valley Stone Quarry Ltd',
            license_no='QRL-2024-002',
            quarry_location='Kochi, Ernakulam'
        )
        dp3 = DealerProfile(
            dealer_id=dealer3.user_id,
            company_name='Highland Enterprise',
            license_no='QRL-2024-003',
            quarry_location='Adimali, Idukki'
        )
        db.session.add_all([dp1, dp2, dp3])

        # 3. Materials (Assigned to Approved Dealers)
        m1 = Material(dealer_id=dealer1.user_id, name='20mm Aggregate', unit='Ton', description='Clean blue metal aggregate for concrete works')
        m2 = Material(dealer_id=dealer1.user_id, name='40mm Aggregate', unit='Ton', description='Heavy duty aggregate for base course & road works')
        m3 = Material(dealer_id=dealer2.user_id, name='Crushed Stone', unit='Ton', description='Crushed quarry stone for foundation')
        m4 = Material(dealer_id=dealer1.user_id, name='Stone Dust', unit='Ton', description='Quarry dust filler material for paving & blocks')
        m5 = Material(dealer_id=dealer2.user_id, name='River Sand', unit='Ton', description='Fine natural river sand for plastering')
        m6 = Material(dealer_id=dealer1.user_id, name='M-Sand', unit='Ton', description='Manufactured sand for plastering and concrete')
        db.session.add_all([m1, m2, m3, m4, m5, m6])
        db.session.flush()

        # 4. Dealer Stocks
        s1 = DealerStock(dealer_id=dealer1.user_id, material_id=m1.material_id, quantity=500.0, price_per_unit=750.0)
        s2 = DealerStock(dealer_id=dealer1.user_id, material_id=m2.material_id, quantity=400.0, price_per_unit=700.0)
        s3 = DealerStock(dealer_id=dealer1.user_id, material_id=m6.material_id, quantity=600.0, price_per_unit=850.0)
        s4 = DealerStock(dealer_id=dealer1.user_id, material_id=m4.material_id, quantity=350.0, price_per_unit=400.0)
        
        s5 = DealerStock(dealer_id=dealer2.user_id, material_id=m1.material_id, quantity=300.0, price_per_unit=760.0)
        s6 = DealerStock(dealer_id=dealer2.user_id, material_id=m5.material_id, quantity=250.0, price_per_unit=1100.0)
        db.session.add_all([s1, s2, s3, s4, s5, s6])

        # 5. Clients
        client1 = User(
            username='ramesh',
            email='ramesh@gmail.com',
            role='client',
            name='Ramesh Kumar',
            phone='9876543210',
            address='Civil Line Road, Pala, Kottayam',
            status='active'
        )
        client1.set_password('client123')

        client2 = User(
            username='anitha',
            email='anitha@gmail.com',
            role='client',
            name='Anitha Nair',
            phone='9876543211',
            address='M.G. Road, Kottayam Town',
            status='active'
        )
        client2.set_password('client123')
        db.session.add_all([client1, client2])
        db.session.flush()

        # 6. Drivers (Under Dealer 1)
        driver_user1 = User(
            username='vijayan_driver',
            email='vijayan@quarry.com',
            role='driver',
            name='Vijayan Pillai',
            phone='9745123456',
            address='Pala South, Kottayam',
            status='active'
        )
        driver_user1.set_password('driver123')

        driver_user2 = User(
            username='sujith_driver',
            email='sujith@quarry.com',
            role='driver',
            name='Sujith Kumar',
            phone='9745987654',
            address='Ettumanoor, Kottayam',
            status='active'
        )
        driver_user2.set_password('driver123')
        db.session.add_all([driver_user1, driver_user2])
        db.session.flush()

        drv1 = Driver(
            user_id=driver_user1.user_id,
            dealer_id=dealer1.user_id,
            license_number='KL-05-2019-8871',
            vehicle_number='KL-05-AB-1234'
        )
        drv2 = Driver(
            user_id=driver_user2.user_id,
            dealer_id=dealer1.user_id,
            license_number='KL-05-2020-4412',
            vehicle_number='KL-05-CD-5678'
        )
        db.session.add_all([drv1, drv2])
        db.session.flush()

        # 7. Orders
        today = date.today()
        o1 = Order(
            client_id=client1.user_id,
            dealer_id=dealer1.user_id,
            material_id=m1.material_id,
            quantity=15.0,
            unit_price=750.0,
            total_price=11250.0,
            delivery_address='Civil Line Road, Pala, Kottayam',
            requested_date=today,
            allocated_driver_id=drv1.driver_id,
            status='Approved'
        )
        o2 = Order(
            client_id=client2.user_id,
            dealer_id=dealer1.user_id,
            material_id=m6.material_id,
            quantity=20.0,
            unit_price=850.0,
            total_price=17000.0,
            delivery_address='M.G. Road, Kottayam Town',
            requested_date=today,
            status='Pending'
        )
        o3 = Order(
            client_id=client1.user_id,
            dealer_id=dealer1.user_id,
            material_id=m4.material_id,
            quantity=10.0,
            unit_price=400.0,
            total_price=4000.0,
            delivery_address='Civil Line Road, Pala, Kottayam',
            requested_date=today - timedelta(days=2),
            allocated_driver_id=drv2.driver_id,
            status='Delivered'
        )
        db.session.add_all([o1, o2, o3])
        db.session.flush()

        # 8. Driver Pass for Order #1
        dp_pass = DriverPass(
            order_id=o1.order_id,
            driver_id=drv1.driver_id,
            dealer_id=dealer1.user_id,
            issue_date=today,
            valid_until=today + timedelta(days=2),
            pass_status='Issued',
            remarks='Priority delivery for concrete slab casting. Gate pass verified.'
        )
        db.session.add(dp_pass)

        # 9. Payment for Delivered Order #3
        p3 = Payment(
            order_id=o3.order_id,
            amount=4000.0,
            payment_method='Online UPI',
            payment_status='Paid',
            transaction_ref='UPI-TXN-984712093'
        )
        db.session.add(p3)

        # 10. Complaint & Feedback
        c1 = Complaint(
            client_id=client1.user_id,
            subject='Inquiry on delivery scheduling',
            message='Can deliveries be arranged early morning around 7 AM?',
            status='Replied',
            admin_reply='Yes, early morning deliveries can be accommodated. Please coordinate with dealer upon order approval.'
        )
        f1 = Feedback(
            client_id=client1.user_id,
            message='Very smooth platform for ordering aggregate and stone dust!',
            rating=5
        )
        r1 = Review(
            client_id=client1.user_id,
            dealer_id=dealer1.user_id,
            rating=5,
            comment='Excellent material quality and prompt vehicle dispatch.'
        )
        db.session.add_all([c1, f1, r1])

        db.session.commit()
        print("Database seeded successfully with initial mock data!")

if __name__ == '__main__':
    seed_database()
