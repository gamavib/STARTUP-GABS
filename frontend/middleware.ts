import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
    const token = request.cookies.get('token')?.value;
    const { pathname } = request.nextUrl;

    // Definir rutas que no requieren autenticación
    const isAuthPage = pathname.startsWith('/login');

    // Si el usuario intenta acceder a una ruta protegida sin token
    if (!token && !isAuthPage) {
        return NextResponse.redirect(new URL('/login', request.url));
    }

    // Si el usuario ya está autenticado y trata de ir al login, redirigir al dashboard
    if (token && isAuthPage) {
        return NextResponse.redirect(new URL('/dashboard', request.url));
    }

    return NextResponse.next();
}

export const config = {
    matcher: [
        /*
         * Match all request paths except for the ones starting with:
         * - api (API routes)
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         */
        '/((?!api|_next/static|_next/image|favicon.ico).*)',
    ],
};