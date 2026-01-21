import AppLayout from '@/components/AppLayout'

export default function AppGroupLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <AppLayout>{children}</AppLayout>
}
