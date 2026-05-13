import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
    const token = request.cookies.get('token')?.value;
    const { pathname } = request.nextUrl;

    // Validación de integridad del token (Silent Validation)
    const isTokenValid = (jwt: string | undefined) => {
        if (!jwt) return false;

        try {
            const parts = jwt.split('.');
            if (parts.length !== 3) return false;

            // Decodificar el payload (segunda parte del JWT)
            // Usamos Buffer en el servidor para decodificar base64
            const payloadBase64 = parts[1];
            const decodedPayload = Buffer.from(payloadBase64, 'base64').toString('utf-8');
            const payload = JSON.parse(decodedPayload);

            // Verificar si el token ha expirado
            const now = Math.floor(Date.now() / 1000);
            if (payload.exp && payload.exp < now) {
                return false;
            }

            return true;
        } catch (e) {
            return false;
        }
    };

    const isAuthenticated = isTokenValid(token);
    const isAuthPage = pathname.startsWith('/login');

    // REQUERIMIENTO CRÍTICO: Siempre redirigir la raíz al login
    if (pathname === '/') {
        return NextResponse.redirect(new URL('/login', request.url));
    }

    // 1. Permitir acceso al login independientemente del estado
    if (isAuthPage) {
        return NextResponse.next();
    }

    // 2. Si el usuario intenta acceder a una ruta protegida sin token válido
    if (!isAuthenticated && !isAuthPage) {
        const response = NextResponse.redirect(new URL('/login', request.url));
        if (token) {
            response.cookies.set('token', '', { path: '/', maxAge: 0 });
        }
        return response;
    }

    return NextResponse.next();
}

export const config = {
    matcher: [
        '/((?!api|_next/static|_next/image|favicon.ico).*)',
    ],
};