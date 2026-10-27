import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/theme.dart';
import '../auth/auth_provider.dart';

/// MedaZone splash screen (Req 18.2, 18.10).
///
/// Background: Dark Green (#1A5C2A).
/// Logo: styled "MedaZone" wordmark centered.
/// Tagline: Amharic — "ሚዳምን ያግኙ. ይዝዙ. ይጫወቱ."
/// Delay 2.5 s, then GoRouter redirect handles navigation based on auth state.
class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _scale;
  late Animation<double> _fade;
  bool _timerFinished = false;

  void _checkAndNavigate() {
    if (!mounted) return;
    if (!_timerFinished) return;

    final authState = ref.read(authProvider);
    if (authState.isLoading) return; // Wait until loading completes

    if (authState.isAuthenticated) {
      context.go('/map');
    } else {
      context.go('/login');
    }
  }

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 900));
    _scale = Tween<double>(begin: 0.72, end: 1.0)
        .animate(CurvedAnimation(parent: _ctrl, curve: Curves.elasticOut));
    _fade = CurvedAnimation(parent: _ctrl, curve: Curves.easeIn);
    _ctrl.forward();
    
    // Just show splash for at least 2.5 s.
    Future.delayed(const Duration(milliseconds: 2500), () {
      if (mounted) {
        setState(() {
          _timerFinished = true;
        });
        _checkAndNavigate();
      }
    });
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    ref.listen<AuthState>(authProvider, (previous, next) {
      if (!next.isLoading) {
        _checkAndNavigate();
      }
    });

    return Scaffold(
      backgroundColor: AppColors.darkGreen, // #1A5C2A
      body: Center(
        child: FadeTransition(
          opacity: _fade,
          child: ScaleTransition(
            scale: _scale,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // ── MedaZone logo (light version on dark green bg) ──────
                Image.asset(
                  'assets/images/logo_light.png', // light logo on dark green background
                  width: 240,
                  fit: BoxFit.contain,
                ),
                const SizedBox(height: 12),

                // ── Amharic tagline — Fix #15 (matches login screen) ─────────
                Text(
                  'ሚዳምን ያግኙ. ይዝዙ. ይጫወቱ.',
                  style: GoogleFonts.inter(
                    fontSize: 15,
                    fontWeight: FontWeight.w400,
                    color: Colors.white.withValues(alpha: 0.85),
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 56),

                // ── Loading spinner ──────────────────────────────────────
                const SizedBox(
                  width: 26,
                  height: 26,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.5,
                    valueColor:
                        AlwaysStoppedAnimation<Color>(AppColors.primaryGreen),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
