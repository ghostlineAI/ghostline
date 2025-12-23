'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  BookOpen,
  Database,
  PenTool,
  CreditCard,
  User,
  LogOut,
} from 'lucide-react';
import { authApi } from '@/lib/api/auth';
import { useAuthStore } from '@/lib/stores/auth';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';

const navigation = [
  { name: 'Projects', href: '/dashboard/projects', icon: BookOpen },
  { name: 'Data Room', href: '/dashboard/data-room', icon: Database },
  { name: 'Create', href: '/dashboard/create', icon: PenTool },
  { name: 'Billing', href: '/dashboard/billing', icon: CreditCard },
  { name: 'Account', href: '/dashboard/account', icon: User },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const logout = useAuthStore((state) => state.logout);

  const handleSignOut = async () => {
    try {
      await authApi.logout();
      logout();
      toast.success('Logged out successfully');
      router.push('/');
    } catch (error) {
      console.error('Error signing out:', error);
      toast.error('Failed to logout');
    }
  };

  return (
    <div className="flex h-full w-64 flex-col bg-gray-900">
      <div className="flex h-16 items-center px-6">
        <h1 className="text-xl font-bold text-white">GhostLine</h1>
      </div>
      
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-gray-800 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              )}
            >
              <item.icon
                className={cn(
                  'mr-3 h-5 w-5 flex-shrink-0',
                  isActive ? 'text-white' : 'text-gray-400 group-hover:text-white'
                )}
              />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-gray-800 p-3">
        <button
          onClick={handleSignOut}
          className="group flex w-full items-center rounded-md px-3 py-2 text-sm font-medium text-gray-300 transition-colors hover:bg-gray-800 hover:text-white"
        >
          <LogOut className="mr-3 h-5 w-5 text-gray-400 group-hover:text-white" />
          Sign Out
        </button>
      </div>
    </div>
  );
} 