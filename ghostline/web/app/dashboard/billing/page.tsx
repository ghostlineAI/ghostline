'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Check } from 'lucide-react';

export default function BillingPage() {
  const plans = [
    {
      id: 'basic',
      name: 'Basic',
      description: 'Perfect for getting started',
      price: 29,
      tokens: 50000,
      features: {
        'AI Writing': true,
        'Voice Analysis': true,
        'Export to PDF': true,
        'Priority Support': false,
        'Collaboration': false,
      }
    },
    {
      id: 'pro',
      name: 'Professional',
      description: 'For serious authors',
      price: 99,
      tokens: 200000,
      features: {
        'AI Writing': true,
        'Voice Analysis': true,
        'Export to PDF': true,
        'Priority Support': true,
        'Collaboration': false,
      }
    },
    {
      id: 'enterprise',
      name: 'Enterprise',
      description: 'For teams and publishers',
      price: 299,
      tokens: 1000000,
      features: {
        'AI Writing': true,
        'Voice Analysis': true,
        'Export to PDF': true,
        'Priority Support': true,
        'Collaboration': true,
      }
    }
  ];

  return (
    <div className="p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Billing & Usage</h1>
        <p className="mt-2 text-gray-600">Manage your subscription and monitor token usage</p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {plans.map((plan) => (
          <Card key={plan.id}>
            <CardHeader>
              <CardTitle>{plan.name}</CardTitle>
              <CardDescription>{plan.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mb-4">
                <p className="text-3xl font-bold">${plan.price}</p>
                <p className="text-gray-600">per month</p>
              </div>
              <div className="mb-4">
                <p className="font-medium">{plan.tokens.toLocaleString()} tokens/month</p>
              </div>
              <div className="space-y-2 mb-4">
                {Object.entries(plan.features).map(([feature, enabled]) => (
                  <div key={feature} className="flex items-center text-sm">
                    <Check className={`mr-2 h-4 w-4 ${enabled ? 'text-green-500' : 'text-gray-300'}`} />
                    <span className={enabled ? '' : 'text-gray-400'}>
                      {feature}
                    </span>
                  </div>
                ))}
              </div>
              <Button className="w-full" variant={plan.id === 'basic' ? 'default' : 'outline'}>
                {plan.id === 'basic' ? 'Current Plan' : 'Upgrade'}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
} 