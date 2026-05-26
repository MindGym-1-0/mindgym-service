// src/app/(dashboard)/layout.tsx

import Sidebar from "../../components/navigation/Sidebar";
import TopBar from "../../components/navigation/TopBar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden bg-[#F6F6F4]">
      
      {/* Fixed Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <div className="ml-[260px] flex flex-1 flex-col overflow-hidden">
        
        {/* Top Navigation */}
        <TopBar />

        {/* Scrollable Content */}
        <main className="flex-1 overflow-y-auto p-8">
          {children}
        </main>
      </div>
    </div>
  );
}