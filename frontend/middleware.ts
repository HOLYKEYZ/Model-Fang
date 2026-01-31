import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Placeholder middleware - no auth for now
// Add authentication later once app is deployed
export function middleware(request: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
  ],
};
