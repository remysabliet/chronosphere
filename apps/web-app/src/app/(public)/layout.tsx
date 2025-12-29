import { Footer } from '@/shared/components/layout/footer'
import { Header } from '@/shared/components/layout/header'

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <>
      <Header />
      <main className="min-h-screen">{children}</main>
      <Footer />
    </>
  )
}
