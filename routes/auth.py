"""
CF Survivor Pool - Authentication Routes
==========================================
Login, register, logout, change password.
"""

import re

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func
from urllib.parse import urlparse

from extensions import db, limiter
from models import User, Week
from timezone_utils import deadline_has_passed

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password')

        user = User.query.filter(
            func.lower(User.username) == username.casefold()
        ).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            if next_page and urlparse(next_page).netloc == '':
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Username validation
        if len(username) < 3:
            flash('Username must be at least 3 characters long.', 'error')
            return render_template('register.html')

        # Email validation
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            flash('Please enter a valid email address.', 'error')
            return render_template('register.html')

        # Password validation
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        existing_username = User.query.filter(
            func.lower(User.username) == username.casefold()
        ).first()
        if existing_username:
            flash('That username already exists.', 'error')
            return render_template('register.html')

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('An account already exists for that email.', 'error')
            return render_template('register.html')

        first_week = Week.query.order_by(Week.week_number).first()
        if first_week and deadline_has_passed(first_week.deadline):
            flash('Registration closed. The pool has already started.', 'error')
            return redirect(url_for('auth.login'))

        new_user = User(username=username, email=email)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('auth.change_password'))

        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('auth.change_password'))

        if current_password == new_password:
            flash('New password must be different from current password.', 'error')
            return redirect(url_for('auth.change_password'))

        if len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return redirect(url_for('auth.change_password'))

        current_user.set_password(new_password)
        db.session.commit()

        flash('Password changed successfully!', 'success')
        return redirect(url_for('main.index'))

    return render_template('change_password.html')
