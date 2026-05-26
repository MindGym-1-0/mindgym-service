// src/app/(main)/settings/page.tsx

"use client";

import { useState } from "react";

import {
  Bell,
  Shield,
  Crown,
  Check,
} from "lucide-react";

export default function SettingsPage() {
  const plans = [
    {
      name: "Free",
      price: "$0",
      features: [
        "3 sessions per month",
        "Basic mood tracking",
        "1 interview tracked",
      ],
      current: false,
    },

    {
      name: "Pro",
      price: "$12/mo",
      features: [
        "Unlimited sessions",
        "Full insights & trends",
        "Unlimited interviews",
        "Coach notes & history",
      ],
      current: true,
    },

    {
      name: "Premium",
      price: "$24/mo",
      features: [
        "Everything in Pro",
        "1:1 human coach calls",
        "Custom session packs",
        "Priority support",
      ],
      current: false,
    },
  ];

  const [notificationSettings, setNotificationSettings] =
    useState([
      {
        title: "Daily mood check-in",
        subtitle: "Prompt at 8:30 AM each morning",
        enabled: true,
      },

      {
        title: "Pre-interview alert",
        subtitle: "2 hours before each booked interview",
        enabled: true,
      },

      {
        title: "Streak reminders",
        subtitle: "If you haven’t opened the app by 7 PM",
        enabled: true,
      },

      {
        title: "Session nudges",
        subtitle: "Suggested moments to reset your mind",
        enabled: false,
      },
    ]);

  const toggleNotification = (title: string) => {
    setNotificationSettings((prev) =>
      prev.map((item) =>
        item.title === title
          ? {
              ...item,
              enabled: !item.enabled,
            }
          : item
      )
    );
  };

  return (
    <div className="min-h-screen bg-[#F6F6F4] px-10 py-8">
      
      {/* Header */}
      <div className="mb-10">
        <p className="text-sm text-gray-500">
          Settings
        </p>

        <h1 className="mt-2 text-4xl font-semibold text-[#111111]">
          Settings
        </h1>
      </div>

      {/* Profile Section */}
      <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
        
        <p className="mb-5 text-xs font-semibold uppercase tracking-wide text-gray-400">
          Profile
        </p>

        <div className="flex items-center justify-between">
          
          <div className="flex items-center gap-4">
            
            <div className="flex h-14 w-14 items-center justify-center rounded-full border border-[#0C6B58] bg-[#DDF4EE] text-sm font-semibold text-[#0C6B58]">
              CZ
            </div>

            <div>
              <h2 className="text-lg font-semibold text-[#111111]">
                Claire Zhu
              </h2>

              <p className="text-sm text-gray-500">
                claire@mindgym.ai
              </p>
            </div>
          </div>

          <button className="rounded-xl border border-gray-200 px-5 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-100">
            Edit profile
          </button>
        </div>
      </div>

      {/* Notifications */}
      <div className="mt-8 rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
        
        <div className="mb-6 flex items-center gap-3">
          <Bell size={20} className="text-[#0C6B58]" />

          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
            Notification Preferences
          </p>
        </div>

        <div className="divide-y divide-gray-100">
          {notificationSettings.map((item) => (
            <div
              key={item.title}
              className="flex items-center justify-between py-5"
            >
              
              <div>
                <h3 className="text-sm font-semibold text-[#111111]">
                  {item.title}
                </h3>

                <p className="mt-1 text-sm text-gray-500">
                  {item.subtitle}
                </p>
              </div>

              {/* Toggle */}
              <button
                onClick={() =>
                  toggleNotification(item.title)
                }
                className={`relative h-7 w-12 rounded-full transition duration-300 ${
                  item.enabled
                    ? "bg-[#0C6B58]"
                    : "bg-gray-300"
                }`}
              >
                <span
                  className={`absolute top-1 h-5 w-5 rounded-full bg-white transition-all duration-300 ${
                    item.enabled
                      ? "right-1"
                      : "left-1"
                  }`}
                />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Account Section */}
      <div className="mt-8 rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
        
        <div className="mb-5 flex items-center gap-3">
          <Shield size={20} className="text-[#0C6B58]" />

          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
            Accounts
          </p>
        </div>

        <div className="flex items-center justify-between">
          
          <div>
            <h3 className="text-sm font-semibold text-[#111111]">
              Delete account
            </h3>

            <p className="mt-1 text-sm text-gray-500">
              Permanently remove your account and all data.
            </p>
          </div>

          <button className="rounded-xl bg-red-500 px-5 py-2 text-sm font-medium text-white transition hover:bg-red-600">
            Delete account
          </button>
        </div>
      </div>

      {/* Pricing Plans */}
      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {plans.map((plan) => (
          <div
            key={plan.name}
            className={`rounded-3xl border p-6 shadow-sm transition ${
              plan.current
                ? "border-[#0C6B58] bg-[#EAF8F4]"
                : "border-gray-200 bg-white"
            }`}
          >
            
            <div className="flex items-center justify-between">
              
              <div>
                <h2 className="text-xl font-semibold text-[#111111]">
                  {plan.name}
                </h2>

                <p className="mt-2 text-3xl font-bold text-[#0C6B58]">
                  {plan.price}
                </p>
              </div>

              {plan.current && (
                <div className="flex items-center gap-2 rounded-full bg-[#DDF4EE] px-3 py-1 text-xs font-semibold text-[#0C6B58]">
                  <Crown size={14} />
                  Current Plan
                </div>
              )}
            </div>

            {/* Features */}
            <div className="mt-8 space-y-4">
              {plan.features.map((feature) => (
                <div
                  key={feature}
                  className="flex items-start gap-3"
                >
                  <Check
                    size={16}
                    className="mt-1 text-[#0C6B58]"
                  />

                  <p className="text-sm text-gray-700">
                    {feature}
                  </p>
                </div>
              ))}
            </div>

            {/* Button */}
            {!plan.current && (
              <button className="mt-8 w-full rounded-xl bg-[#0C6B58] py-3 text-sm font-medium text-white transition hover:bg-[#095746]">
                Upgrade
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}