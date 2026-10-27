import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'auth_provider.dart';
import '../../core/theme.dart';
import '../../shared/widgets/primary_button.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});
  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _phoneCtrl    = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _formKey      = GlobalKey<FormState>();
  bool _obscure       = true;

  @override
  void dispose() {
    _phoneCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    try {
      await ref.read(authProvider.notifier).login(
            _phoneCtrl.text.trim(),
            _passwordCtrl.text,
          );
      // GoRouter redirect handles navigation to /map
    } catch (_) {}
  }

  // Fix #16: clear auth error as soon as the user starts re-typing
  void _onFieldChanged(String _) {
    if (ref.read(authProvider).error != null) {
      ref.read(authProvider.notifier).clearError();
    }
  }

  // Fix #7: show support contact dialog for password reset
  void _showForgotPassword() {
    showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Reset Password'),
        content: const Text(
          'To reset your password, please contact our support team:\n\n'
          '\u{1F4DE} +251 900 000 000\n'
          '\u{1F4AC} WhatsApp: +251 900 000 000\n'
          '\u{1F4E7} support@medazone.et',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 40),

                // Logo
                Center(
                  child: Builder(
                    builder: (ctx) {
                      final isDark = Theme.of(ctx).brightness == Brightness.dark;
                      return Image.asset(
                        isDark
                            ? 'assets/images/logo_light.png'
                            : 'assets/images/logo_dark.png',
                        width: 200,
                        fit: BoxFit.contain,
                      );
                    },
                  ),
                ),
                const SizedBox(height: 8),
                // Fix #15: unified Amharic tagline
                Text(
                  '\u121a\u12ee\u12f3\u121d\u1295 \u12eb\u130d\u129\u09d9. \u12ed\u12d8\u12d1. \u12ed\u1338\u12c8\u1271.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(fontSize: 15),
                ),
                const SizedBox(height: 48),

                // Error banner
                if (auth.error != null) ...[
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: AppColors.redBg,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppColors.red.withOpacity(0.3)),
                    ),
                    child: Text(auth.error!,
                        style: const TextStyle(color: AppColors.red, fontSize: 13)),
                  ),
                  const SizedBox(height: 16),
                ],

                // Phone
                TextFormField(
                  controller: _phoneCtrl,
                  keyboardType: TextInputType.phone,
                  onChanged: _onFieldChanged, // Fix #16
                  decoration: const InputDecoration(
                    labelText: 'Phone Number',
                    hintText: '+251 9XX XXX XXX',
                    prefixIcon: Icon(Icons.phone_outlined),
                  ),
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) return 'Enter your phone number';
                    final d = v.replaceAll(RegExp(r'[\s\-()]'), '');
                    if (!RegExp(r'^(\+|0)\d{9,}$').hasMatch(d)) return 'Use format: +2519XXXXXXXX';
                    return null;
                  },
                ),
                const SizedBox(height: 16),

                // Password
                TextFormField(
                  controller: _passwordCtrl,
                  obscureText: _obscure,
                  onChanged: _onFieldChanged, // Fix #16
                  decoration: InputDecoration(
                    labelText: 'Password',
                    prefixIcon: const Icon(Icons.lock_outline),
                    suffixIcon: IconButton(
                      icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                      onPressed: () => setState(() => _obscure = !_obscure),
                    ),
                  ),
                  validator: (v) {
                    if (v == null || v.isEmpty) return 'Enter your password';
                    if (v.length < 6) return 'Password must be at least 6 characters';
                    return null;
                  },
                ),

                // Fix #7: Forgot Password link
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(
                    onPressed: _showForgotPassword,
                    child: const Text('Forgot Password?',
                        style: TextStyle(color: AppColors.primaryGreen, fontSize: 13)),
                  ),
                ),

                const SizedBox(height: 8),

                PrimaryButton(
                  label: 'Sign In',
                  isLoading: auth.isLoading,
                  onPressed: auth.isLoading ? null : _login,
                ),

                const SizedBox(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text("Don't have an account? ",
                        style: Theme.of(context).textTheme.bodyMedium),
                    GestureDetector(
                      onTap: () => context.go('/register'),
                      child: const Text('Sign Up',
                          style: TextStyle(
                              color: AppColors.primaryGreen,
                              fontWeight: FontWeight.w600,
                              fontSize: 14)),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
