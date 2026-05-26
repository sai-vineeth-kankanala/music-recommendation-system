import json

def test_register_and_login_flow(client):
    # 1. Register a new user
    reg_payload = {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "Password123"
    }
    response = client.post('/api/auth/register', json=reg_payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data['message'] == 'User registered successfully.'
    assert 'user' in data
    assert data['user']['username'] == 'testuser'
    assert data['user']['email'] == 'testuser@example.com'

    # 2. Try to register with duplicate email
    response = client.post('/api/auth/register', json=reg_payload)
    assert response.status_code == 409

    # 3. Try to register with weak password
    weak_payload = {
        "username": "testuser2",
        "email": "testuser2@example.com",
        "password": "weak"
    }
    response = client.post('/api/auth/register', json=weak_payload)
    assert response.status_code == 400

    # 4. Login user
    login_payload = {
        "email": "testuser@example.com",
        "password": "Password123"
    }
    response = client.post('/api/auth/login', json=login_payload)
    assert response.status_code == 200
    data = response.get_json()
    assert 'access_token' in data
    assert 'refresh_token' in data
    access_token = data['access_token']
    refresh_token = data['refresh_token']

    # 5. Get user profile (authenticated)
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = client.get('/api/users/profile', headers=headers)
    assert response.status_code == 200
    profile = response.get_json()
    assert profile['username'] == 'testuser'

    # 6. Get user profile (unauthenticated)
    response = client.get('/api/users/profile')
    assert response.status_code == 401

    # 7. Update user profile
    update_payload = {
        "username": "updateduser"
    }
    response = client.put('/api/users/profile', json=update_payload, headers=headers)
    assert response.status_code == 200
    profile_updated = response.get_json()
    assert profile_updated['user']['username'] == 'updateduser'

    # 8. Token refresh flow
    refresh_payload = {
        "refresh_token": refresh_token
    }
    response = client.post('/api/auth/refresh', json=refresh_payload)
    assert response.status_code == 200
    refresh_data = response.get_json()
    assert 'access_token' in refresh_data

    # 9. Logout
    response = client.post('/api/auth/logout')
    assert response.status_code == 200
