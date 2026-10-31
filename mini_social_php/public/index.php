<?php require_once __DIR__.'/../app/bootstrap.php'; header('Location: '.(currentUser()?'feed.php':'login.php')); exit;
