<?php require_once __DIR__.'/../app/bootstrap.php'; header('Location: '.(isLoggedIn()?'feed.php':'login.php')); exit;
