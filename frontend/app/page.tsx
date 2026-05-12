import { redirect } from 'next/navigation';

export default function RootPage() {
    // Redirigimos automáticamente la raíz al login para asegurar que el usuario entre por el flujo de seguridad
    redirect('/login');
    return null;
}
