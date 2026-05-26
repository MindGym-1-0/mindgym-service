import Sidebar from "../../components/navigation/Sidebar";
import TopBar from "../../components/navigation/TopBar";

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen bg-[#F6F6F4]">
      <Sidebar />

      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar />

        <main className="flex-1 overflow-y-auto p-8">
          {children}
        </main>
      </div>
    </div>
  );
}