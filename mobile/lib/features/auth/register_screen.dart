import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'auth_provider.dart';
import '../../core/theme.dart';
import '../../shared/widgets/brand_app_bar.dart';
import '../../shared/widgets/primary_button.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});
  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _nameCtrl     = TextEditingController();
  final _phoneCtrl    = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _confirmCtrl  = TextEditingController();
  final _formKey      = GlobalKey<FormState>();
  bool _obscure       = true;
  final List<String> _positions = [];

  static const _allPositions = ['Goalkeeper', 'Defender', 'Midfielder', 'Forward', 'Any'];

  @override
  void dispose() {
    _nameCtrl.dispose();
    _phoneCtrl.dispose();
    _passwordCtrl.dispose();
    _confirmCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    try {
      await ref.read(authProvider.notifier).register(
            _phoneCtrl.text.trim(),
            _passwordCtrl.text,
            displayName: _nameCtrl.text.trim(),
          );
      // GoRouter redirect navigates to /map
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);

    return Scaffold(
      appBar: const BrandAppBar(),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('Create Account',
                    style: Theme.of(context).textTheme.headlineMedium),
                const SizedBox(height: 6),
                Text('Join MedaZone and start booking fields.',
                    style: Theme.of(context).textTheme.bodySmall),
                const SizedBox(height: 28),

                // Error
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

                // Display name
                TextFormField(
                  controller: _nameCtrl,
                  textCapitalization: TextCapitalization.words,
                  decoration: const InputDecoration(
                    labelText: 'Display Name',
                    hintText: 'Abebe Bikila',
                    prefixIcon: Icon(Icons.person_outline),
                  ),
                  validator: (v) => (v == null || v.trim().length < 2)
                      ? 'Enter a name (min 2 characters)'
                      : null,
                ),
                const SizedBox(height: 16),

                // Phone
                TextFormField(
                  controller: _phoneCtrl,
                  keyboardType: TextInputType.phone,
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
                  decoration: InputDecoration(
                    labelText: 'Password',
                    prefixIcon: const Icon(Icons.lock_outline),
                    suffixIcon: IconButton(
                      icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                      onPressed: () => setState(() => _obscure = !_obscure),
                    ),
                  ),
                  validator: (v) {
                    if (v == null || v.isEmpty) return 'Enter a password';
                    if (v.length < 6) return 'Password must be at least 6 characters';
                    return null;
                  },
                ),
                const SizedBox(height: 16),

                // Confirm password
                TextFormField(
                  controller: _confirmCtrl,
                  obscureText: _obscure,
                  decoration: const InputDecoration(
                    labelText: 'Confirm Password',
                    prefixIcon: Icon(Icons.lock_outline),
                  ),
                  validator: (v) => v != _passwordCtrl.text ? 'Passwords do not match' : null,
                ),
                const SizedBox(height: 20),

                // Preferred positions (optional)
                Text('Preferred Positions (optional)',
                    style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8, runSpacing: 8,
                  children: _allPositions.map((pos) {
                    final selected = _positions.contains(pos);
                    return FilterChip(
                      label: Text(pos),
                      selected: selected,
                      onSelected: (_) => setState(() {
                        if (selected) _positions.remove(pos);
                        else _positions.add(pos);
                      }),
                      selectedColor: AppColors.primaryGreen.withOpacity(0.15),
                      checkmarkColor: AppColors.primaryGreen,
                    );
                  }).toList(),
                ),
                const SizedBox(height: 32),

                PrimaryButton(
                  label: 'Create Account',
                  isLoading: auth.isLoading,
                  onPressed: auth.isLoading ? null : _submit,
                ),
                const SizedBox(height: 12),
                TextButton(
                  onPressed: () => context.go('/login'),
                  child: const Text('Already have an account? Sign In',
                      style: TextStyle(color: AppColors.primaryGreen)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
