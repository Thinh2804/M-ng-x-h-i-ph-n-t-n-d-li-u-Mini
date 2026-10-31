<?php require_once __DIR__.'/../app/bootstrap.php'; unset($_SESSION[SESSION_USER_KEY]); session_regenerate_id(true); header('Location: login.php'); exit;
