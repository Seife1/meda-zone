// Local SQLite cache for MedaZone fields and bookings.
//
// `cached_at` is stored as a UTC Unix timestamp (seconds since epoch).
// To show "Updated X min ago" in the UI, convert with:
//   DateTime.fromMillisecondsSinceEpoch(cachedAt * 1000, isUtc: true).toLocal()
//
// TTL for fields cache: AppConstants.fieldCacheTtlMinutes (10 min).
// Bookings are never auto-expired — they are refreshed on demand.

import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';
import 'dart:convert';
import 'constants.dart';

class LocalDb {
  LocalDb._();
  static final LocalDb instance = LocalDb._();

  Database? _db;

  Future<Database> _ensureDb() async {
    if (_db != null) return _db!;
    final dir = await getDatabasesPath();
    final path = join(dir, 'medazone.db');
    _db = await openDatabase(
      path,
      version: 1,
      onCreate: (db, _) async {
        await db.execute('''
          CREATE TABLE fields_cache (
            id        TEXT PRIMARY KEY,
            data      TEXT NOT NULL,
            cached_at INTEGER NOT NULL
          )
        ''');
        await db.execute('''
          CREATE TABLE bookings_cache (
            id        TEXT PRIMARY KEY,
            data      TEXT NOT NULL,
            cached_at INTEGER NOT NULL
          )
        ''');
      },
    );
    return _db!;
  }

  // ── Fields ──────────────────────────────────────────────────────────────────

  /// Insert or replace a list of field maps in the cache.
  Future<void> upsertFields(List<Map<String, dynamic>> fields) async {
    if (fields.isEmpty) return;
    final db = await _ensureDb();
    final ts = DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000;
    final batch = db.batch();
    for (final f in fields) {
      batch.insert(
        'fields_cache',
        {
          'id': f['id'] as String,
          'data': jsonEncode(f),
          'cached_at': ts,
        },
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    }
    await batch.commit(noResult: true);
  }

  /// Returns all cached fields (regardless of TTL).
  Future<List<Map<String, dynamic>>> getFields() async {
    final db = await _ensureDb();
    final rows = await db.query('fields_cache');
    return rows
        .map((r) => jsonDecode(r['data'] as String) as Map<String, dynamic>)
        .toList();
  }

  /// Deletes fields cached more than [AppConstants.fieldCacheTtlMinutes] ago.
  Future<void> clearExpiredFields() async {
    final db = await _ensureDb();
    final cutoff = DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000 -
        AppConstants.fieldCacheTtlMinutes * 60;
    await db.delete(
      'fields_cache',
      where: 'cached_at < ?',
      whereArgs: [cutoff],
    );
  }

  // ── Bookings ─────────────────────────────────────────────────────────────────

  /// Insert or replace a list of booking maps in the cache.
  Future<void> upsertBookings(List<Map<String, dynamic>> bookings) async {
    if (bookings.isEmpty) return;
    final db = await _ensureDb();
    final ts = DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000;
    final batch = db.batch();
    for (final b in bookings) {
      batch.insert(
        'bookings_cache',
        {
          'id': b['id'] as String,
          'data': jsonEncode(b),
          'cached_at': ts,
        },
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    }
    await batch.commit(noResult: true);
  }

  /// Returns all cached bookings.
  Future<List<Map<String, dynamic>>> getBookings() async {
    final db = await _ensureDb();
    final rows = await db.query('bookings_cache');
    return rows
        .map((r) => jsonDecode(r['data'] as String) as Map<String, dynamic>)
        .toList();
  }
}

/// Convenience singleton for direct use throughout the app.
final localDb = LocalDb.instance;
