import unittest
from datetime import date, timedelta
from app import app
from models import db, User, DealerProfile, Driver, Material, DealerStock, Order, DriverPass

class QuarryManagementTestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def login(self, username, password):
        return self.client.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    # 1. Test Authentication & Dashboard Routing
    def test_auth_and_dashboards(self):
        # Admin Login
        res = self.login('admin', 'admin123')
        self.assertIn(b'Administrator Dashboard', res.data)
        self.logout()

        # Dealer Login
        res = self.login('apex_quarry', 'dealer123')
        self.assertIn(b'Quarry Stock Management', res.data)
        self.assertIn(b'Driver Pass', res.data)
        self.logout()

        # Client Login
        res = self.login('ramesh', 'client123')
        self.assertIn(b'Welcome, Ramesh Kumar', res.data)
        self.logout()

        # Driver Login
        res = self.login('vijayan_driver', 'driver123')
        self.assertIn(b'Driver Delivery Dashboard', res.data)
        self.assertIn(b'Driver Passes', res.data)
        self.logout()

    # 2. Test Dealer Driver Pass Creation & API Endpoints
    def test_driver_pass_workflow(self):
        # Login as Dealer
        self.login('apex_quarry', 'dealer123')

        # Test Order API endpoint
        res = self.client.get('/dealer/api/order_info/1')
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertEqual(json_data['client_name'], 'Ramesh Kumar')
        self.assertEqual(json_data['material_name'], '20mm Aggregate')

        # Test Driver API endpoint
        res = self.client.get('/dealer/api/driver_info/1')
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertEqual(json_data['vehicle_number'], 'KL-05-AB-1234')

        # Create a new order for testing pass creation
        with app.app_context():
            order2 = Order.query.get(2) # Pending order #2 (Anitha Nair, M-Sand)
            order2.status = 'Approved'
            db.session.commit()

        # Submit Pass Creation Form for Order #2
        today_str = date.today().strftime('%Y-%m-%d')
        future_str = (date.today() + timedelta(days=3)).strftime('%Y-%m-%d')

        res = self.client.post('/dealer/driver_pass/create', data=dict(
            order_id='2',
            driver_id='2', # Sujith Kumar
            valid_until=future_str,
            remarks='Site clearance pass.'
        ), follow_redirects=True)

        self.assertIn(b'QUARRY MANAGEMENT SYSTEM', res.data)
        self.assertIn(b'DRIVER DELIVERY PASS', res.data)
        self.assertIn(b'Anitha Nair', res.data)
        self.assertIn(b'M-Sand', res.data)
        self.assertIn(b'KL-05-CD-5678', res.data)
        self.assertIn(b'Site clearance pass.', res.data)

        # Test Duplicate Pass Prevention Validation
        res_dup = self.client.post('/dealer/driver_pass/create', data=dict(
            order_id='2',
            driver_id='2',
            valid_until=future_str,
            remarks='Duplicate pass attempt'
        ), follow_redirects=True)

        self.assertIn(b'already exists for Order #2', res_dup.data)

        # Test Invalid Valid Until Date Validation (valid_until < issue_date)
        past_str = (date.today() - timedelta(days=2)).strftime('%Y-%m-%d')
        
        # Create Order #4 for date testing
        with app.app_context():
            client1 = User.query.filter_by(username='ramesh').first()
            dealer1 = User.query.filter_by(username='apex_quarry').first()
            mat = Material.query.first()

            order4 = Order(
                client_id=client1.user_id,
                dealer_id=dealer1.user_id,
                material_id=mat.material_id,
                quantity=5.0,
                unit_price=750.0,
                total_price=3750.0,
                delivery_address='Test Pala Address',
                requested_date=date.today(),
                status='Approved'
            )
            db.session.add(order4)
            db.session.commit()
            order4_id = order4.order_id

        res_date_err = self.client.post('/dealer/driver_pass/create', data=dict(
            order_id=str(order4_id),
            driver_id='1',
            valid_until=past_str,
            remarks='Test invalid date'
        ), follow_redirects=True)

        self.assertIn(b'Valid Until date cannot be earlier than the Issue Date', res_date_err.data)
        self.logout()

    # 3. Test Driver Module Integration & Delivery Completion
    def test_driver_module(self):
        # Login as Driver 1
        self.login('vijayan_driver', 'driver123')

        # View Driver Passes page
        res = self.client.get('/driver/passes')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'My Driver Passes', res.data)
        self.assertIn(b'#PASS-1', res.data)
        self.assertIn(b'Ramesh Kumar', res.data)
        self.assertIn(b'20mm Aggregate', res.data)

        # Confirm delivery for Order #1
        res_deliv = self.client.post('/driver/confirm_delivery/1', follow_redirects=True)
        self.assertIn(b'confirmed as DELIVERED', res_deliv.data)

        # Verify associated pass status updated to Completed
        with app.app_context():
            dp = DriverPass.query.filter_by(order_id=1).first()
            self.assertEqual(dp.pass_status, 'Completed')

        self.logout()

if __name__ == '__main__':
    unittest.main()
