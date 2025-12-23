// Learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom'

// Mock next/router
jest.mock('next/router', () => ({
  useRouter() {
    return {
      route: '/',
      pathname: '',
      query: '',
      asPath: '',
      push: jest.fn(),
      events: {
        on: jest.fn(),
        off: jest.fn()
      },
      beforePopState: jest.fn(() => null),
      prefetch: jest.fn(() => null)
    };
  },
}));

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter() {
    return {
      push: jest.fn(),
      replace: jest.fn(),
      prefetch: jest.fn(),
      back: jest.fn(),
    };
  },
  useSearchParams() {
    return new URLSearchParams();
  },
  usePathname() {
    return '';
  },
}));

// Mock environment variables for tests
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'

// Mock window.matchMedia only if window is defined
if (typeof window !== 'undefined') {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation(query => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(), // deprecated
      removeListener: jest.fn(), // deprecated
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  });
}

// Mock Radix UI components
jest.mock('@radix-ui/react-dialog', () => ({
  Root: ({ children, ...props }) => children,
  Trigger: ({ children, ...props }) => children,
  Portal: ({ children, ...props }) => children,
  Overlay: ({ children, ...props }) => children,
  Content: ({ children, ...props }) => children,
  Title: ({ children, ...props }) => children,
  Description: ({ children, ...props }) => children,
  Close: ({ children, ...props }) => children,
}));

jest.mock('@radix-ui/react-alert-dialog', () => ({
  Root: ({ children, ...props }) => children,
  Trigger: ({ children, ...props }) => children,
  Portal: ({ children, ...props }) => children,
  Overlay: ({ children, ...props }) => children,
  Content: ({ children, ...props }) => children,
  Title: ({ children, ...props }) => children,
  Description: ({ children, ...props }) => children,
  Cancel: ({ children, ...props }) => children,
  Action: ({ children, ...props }) => children,
})); 