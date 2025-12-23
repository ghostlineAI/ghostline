-- Clear existing test user
TRUNCATE TABLE users CASCADE;

-- Insert the correct user
INSERT INTO users (
    id,
    email,
    username,
    full_name,
    hashed_password,
    is_active,
    is_verified,
    token_balance,
    created_at,
    updated_at
) VALUES (
    gen_random_uuid(),
    'alexgrgs2314@gmail.com',
    'alexgrgs2314',
    'Alex Georges',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYvXnAJrTC', -- This is hashed "password123"
    true,
    true,
    100000,
    NOW(),
    NOW()
);

-- Verify
SELECT id, email, username, token_balance FROM users WHERE email = 'alexgrgs2314@gmail.com'; 