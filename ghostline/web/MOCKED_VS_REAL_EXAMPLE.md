# Mocked vs Real Tests: Side by Side

## Example 1: Testing Login

### ❌ Mocked Test (What We Had)
```typescript
it('should successfully login', async () => {
  // Mock the API response
  mockApiClient.post.mockResolvedValueOnce({
    data: {
      access_token: 'fake-token',
      token_type: 'bearer',
    }
  });

  const result = await authApi.login({
    email: 'test@example.com',
    password: 'password'
  });

  expect(result.access_token).toBe('fake-token');
});
```

**Problems:**
- Doesn't test real authentication
- Doesn't catch CORS issues
- Doesn't test 307 redirects
- Doesn't validate real response format

### ✅ Real Test (What We Need)
```typescript
it('should successfully login', async () => {
  // Make real API call
  const response = await axios.post('http://localhost:8000/api/v1/auth/login/', {
    email: 'test@example.com',
    password: 'realpassword'
  });

  expect(response.status).toBe(200);
  expect(response.data.access_token).toBeDefined();
  expect(response.data.token_type).toBe('bearer');
  
  // Test the token actually works
  const meResponse = await axios.get('/users/me/', {
    headers: { Authorization: `Bearer ${response.data.access_token}` }
  });
  expect(meResponse.status).toBe(200);
});
```

**Benefits:**
- Tests real authentication flow
- Catches CORS issues immediately
- Validates actual API behavior
- Tests token functionality

## Example 2: Testing Project Creation

### ❌ Mocked Test
```typescript
it('should create project', async () => {
  mockApiClient.post.mockResolvedValueOnce({
    data: { id: '123', name: 'Test Project' }
  });

  const result = await projectsApi.create({
    name: 'Test Project',
    genre: 'FICTION' // Wrong! Should be lowercase
  });

  expect(result.id).toBe('123');
});
```

**This test passed but the real API failed!**

### ✅ Real Test
```typescript
it('should create project', async () => {
  const token = await getAuthToken(); // Real auth
  
  const response = await axios.post('/projects/', {
    name: 'Test Project',
    genre: 'fiction' // Correct format discovered by real test
  }, {
    headers: { Authorization: `Bearer ${token}` }
  });

  expect(response.status).toBe(201);
  expect(response.data.id).toBeDefined();
  expect(response.data.genre).toBe('fiction');
});
```

## What Mocked Tests Miss

1. **HTTP Status Codes**
   - Mocked: Always returns what you tell it
   - Real: Actual 307, 401, 422, 500 errors

2. **CORS Headers**
   - Mocked: No CORS simulation
   - Real: Real preflight requests and CORS errors

3. **Response Formats**
   - Mocked: Whatever you mock
   - Real: Actual API response structure

4. **Network Issues**
   - Mocked: No network simulation
   - Real: Timeouts, connection errors

5. **Authentication Flow**
   - Mocked: Fake tokens
   - Real: Real JWT validation

## When to Use Each

### Use Mocked Tests For:
- UI component behavior
- Business logic functions
- Error handling scenarios
- Fast feedback during development

### Use Real Tests For:
- API integration
- Authentication flows
- End-to-end workflows
- Pre-deployment validation

## The Lesson

Our mocked tests gave us **false confidence**. They tested our assumptions, not reality. The 307 redirect CORS issue would have been caught immediately with real tests. 