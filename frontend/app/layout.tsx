import './globals.css';
import Providers from './providers';

export const metadata = {
  title: 'SaaS Actuarial - Optimization Platform',
  description: 'B2B platform for Reinsurance Optimization and Capital Management',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}