class Review {
  final String id;
  final String playerId;
  final String fieldId;
  final String bookingId;
  final int rating;
  final String? reviewText;
  final String createdAt;

  const Review({
    required this.id,
    required this.playerId,
    required this.fieldId,
    required this.bookingId,
    required this.rating,
    this.reviewText,
    required this.createdAt,
  });

  factory Review.fromJson(Map<String, dynamic> j) => Review(
        id: j['id'] as String,
        playerId: j['player_id'] as String,
        fieldId: j['field_id'] as String,
        bookingId: j['booking_id'] as String,
        rating: j['rating'] as int,
        reviewText: j['review_text'] as String?,
        createdAt: j['created_at'] as String,
      );
}
