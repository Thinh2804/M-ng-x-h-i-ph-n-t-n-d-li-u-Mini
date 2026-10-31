<?php
// Central configuration. Change API_BASE_URL to the PC4 address reachable from this browser/server.
define('API_BASE_URL', getenv('API_BASE_URL') ?: 'http://127.0.0.1:8000');
define('APP_NAME', 'MiniSocial');
define('SESSION_USER_KEY', 'social_user');
