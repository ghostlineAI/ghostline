/**
 * Node.js E2E test for file upload functionality
 * This runs outside of Jest/JSDOM to avoid CORS issues
 */

const axios = require('axios');
const FormData = require('form-data');

const API_URL = 'https://api.dev.ghostline.ai/api/v1';

async function runFileUploadE2ETest() {
  console.log('🧪 Running File Upload E2E Test in Node.js...\n');
  
  const timestamp = Date.now();
  const testUser = {
    email: `node_test_${timestamp}@example.com`,
    password: 'TestPass123!',
    username: `nodetest_${timestamp}`,
    full_name: 'Node Test User'
  };
  
  try {
    // 1. Register user
    console.log('1️⃣ Registering test user...');
    try {
      await axios.post(`${API_URL}/auth/register`, testUser);
      console.log('   ✅ User registered');
    } catch (error) {
      if (error.response?.status === 400) {
        console.log('   ℹ️  User might already exist');
      } else {
        throw error;
      }
    }
    
    // 2. Login
    console.log('\n2️⃣ Logging in...');
    const loginResponse = await axios.post(`${API_URL}/auth/login`, {
      email: testUser.email,
      password: testUser.password
    });
    const token = loginResponse.data.access_token;
    console.log('   ✅ Logged in successfully');
    
    // 3. Create project
    console.log('\n3️⃣ Creating test project...');
    const projectResponse = await axios.post(
      `${API_URL}/projects/`,
      {
        title: `Node E2E Test Project ${timestamp}`,
        genre: 'fiction',
        description: 'Testing file uploads from Node.js'
      },
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );
    const projectId = projectResponse.data.id;
    console.log(`   ✅ Project created: ${projectId}`);
    
    // 4. Upload file
    console.log('\n4️⃣ Uploading test file...');
    const form = new FormData();
    form.append('file', Buffer.from('This is a test file from Node.js E2E test'), {
      filename: 'node_test.txt',
      contentType: 'text/plain'
    });
    form.append('project_id', projectId);
    
    const uploadResponse = await axios.post(
      `${API_URL}/source-materials/upload`,
      form,
      {
        headers: {
          ...form.getHeaders(),
          Authorization: `Bearer ${token}`
        }
      }
    );
    
    console.log('   ✅ File uploaded successfully!');
    console.log(`   📄 File ID: ${uploadResponse.data.id}`);
    console.log(`   📄 Status: ${uploadResponse.data.status}`);
    
    // 5. List files
    console.log('\n5️⃣ Listing project files...');
    const listResponse = await axios.get(
      `${API_URL}/projects/${projectId}/source-materials`,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );
    console.log(`   ✅ Found ${listResponse.data.length} files`);
    
    // 6. Test duplicate handling
    console.log('\n6️⃣ Testing duplicate file handling...');
    const dupResponse = await axios.post(
      `${API_URL}/source-materials/upload`,
      form,
      {
        headers: {
          ...form.getHeaders(),
          Authorization: `Bearer ${token}`
        }
      }
    );
    console.log(`   ✅ Duplicate handled: ${dupResponse.data.duplicate ? 'Yes' : 'No'}`);
    
    console.log('\n✅ All E2E tests passed! File upload is working correctly.\n');
    
  } catch (error) {
    console.error('\n❌ Test failed:', error.response?.data || error.message);
    process.exit(1);
  }
}

// Run the test
runFileUploadE2ETest(); 