// Dummy firebase-messaging-sw.js for web dev bypassing FCM
self.addEventListener('push', function(e) {
  console.log('[FCM Web] Dummy push event received.');
});
