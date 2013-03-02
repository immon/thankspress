from flask import render_template, flash, redirect, url_for, g, session, request
from flask.ext.login import current_user, login_user, login_required, logout_user

from app import app, db, lm
from app.emails import email_verification, follower_notification
from app.user.forms import SettingsPasswordChangeForm, SettingsProfileForm, SettingsEmailsForm, \
    SettingsAccountPickUsernameForm, SettingsAccountForm, SignInForm, SignUpForm
from app.user.models import Email, Follow, User, UserProfile
from app.functions import Functions

from datetime import datetime

@lm.user_loader
def load_user(id):
    return User.get_user(int(id))

@app.before_request
def before_request():
    g.user = current_user
    if g.user.is_authenticated():
        g.user.date_last_acted = datetime.utcnow()
        db.session.add(g.user)
        db.session.commit()
        if g.user.is_activated():
            pass
        elif g.user.is_new() and request.endpoint != 'sign_out':
            form = SettingsAccountPickUsernameForm()
            if form.validate_on_submit():
                g.user.username = form.username.data
                g.user.make_activated()
                db.session.add(g.user)
                db.session.commit()
                flash('Welcome to ThanksPress!')
                return redirect(url_for('user_timeline', username = g.user.username))
            else:
                return render_template('user/settings_account_pick_username.html',
                    form = form,
                    title = 'Pick Username')
        elif g.user.is_deactivated():
            g.user.make_activated()
            db.session.add(g.user)
            db.session.commit()
            flash('Great to see you back!')

# Registration -------------------------------------

@app.route('/sign-in/', methods = ['GET', 'POST'])
def sign_in():
    if g.user.is_authenticated():
        flash("You are already registered.")
        return redirect(url_for('user_timeline', username = g.user.username))
    form = SignInForm()
    if form.validate_on_submit():
            login_user(form.user, remember = form.remember_me.data)
            g.user.date_last_signed_in = datetime.utcnow()
            db.session.add(g.user)
            db.session.commit()
            return redirect(request.args.get("next") or url_for('news_feed'))
    return render_template('user/sign_in.html',
        form = form,
        title = 'Sign In',
        message = '/sign-in')

@app.route('/sign-out/')
def sign_out():
    logout_user()
    return redirect(url_for('news_feed'))

@app.route('/sign-up/', methods = ['GET', 'POST'])
def sign_up():
    if g.user.is_authenticated():
        flash("You are already registered.")
        return redirect(url_for('user_timeline', username = g.user.username))
    form = SignUpForm()
    if form.validate_on_submit():
        #Register user's Account
        user = User(password = form.password.data)
        db.session.add(user)
        db.session.commit()
        #Register user's Profile
        user_profile = UserProfile(user_id = user.id, name = form.name.data)
        db.session.add(user_profile)
        #Register user's Email
        email = Email(user_id = user.id, email = form.email.data, is_primary = True)
        db.session.add(email)
        #Follow user's self
        follow = Follow(follower_id = user.id, followed_id = user.id)
        db.session.add(follow)
        db.session.commit()
        #Redirect to Sign In
        flash('You have successfully signed up for ThanksPress.')
        return redirect(url_for('sign_in'))
    return render_template('user/sign_up.html',
        form = form,
        title = 'Sign Up',
        message = "/sign-up")

# Settings ---------------------------------------

@app.route('/settings/', methods = ['GET', 'POST'])
@app.route('/settings/account/', methods = ['GET', 'POST'])
@login_required
def settings_account():
    form = SettingsAccountForm(g.user)
    if form.validate_on_submit():
        g.user.username = form.username.data
        db.session.add(g.user)
        db.session.commit()
        flash('Changes have been saved.')
        return redirect(url_for('settings'))
    else:
        form.username.data = g.user.username
    return render_template('user/settings_account.html',
        form = form,
        title = 'Account Settings for' + g.user.username)

@app.route('/settings/change-password/', methods = ['GET', 'POST'])
@login_required
def settings_change_password():
    form = SettingsPasswordChangeForm(g.user)
    if form.validate_on_submit():
        g.user.change_password(form.new_password.data)
        db.session.add(g.user)
        db.session.commit()
        flash('You have successfully changed your password.')
    return render_template("user/settings_change_password.html",
        form = form,
        title = "Change Password")

@app.route('/settings/deactivate/', methods = ['GET','POST'])
@login_required
def settings_deactivate():
    form = SignInForm()
    if form.validate_on_submit():
        form.user.make_deactivated()
        db.session.add(form.user)
        db.session.commit()
        return sign_out()
    return render_template('user/settings_deactivate.html',
        form = form,
        title = 'Deactivate Account')

@app.route('/settings/profile/', methods = ['GET', 'POST'])
@login_required
def settings_profile():
    form = SettingsProfileForm()
    if form.validate_on_submit():
        g.user.profile.name = form.name.data
        g.user.profile.bio = form.bio.data
        g.user.profile.facebook_username = form.facebook_username.data
        g.user.profile.is_facebook_visible = form.is_facebook_visible.data
        g.user.profile.twitter_username = form.twitter_username.data
        g.user.profile.is_twitter_visible = form.is_twitter_visible.data
        g.user.profile.website = form.website.data
        db.session.add(g.user.profile)
        db.session.commit()
        flash('Changes have been saved.')
        return redirect(url_for('settings_profile'))
    else:
        form.name.data = g.user.profile.name
        form.bio.data = g.user.profile.bio
        form.facebook_username.data = g.user.profile.facebook_username
        form.is_facebook_visible.data = g.user.profile.is_facebook_visible
        form.twitter_username.data = g.user.profile.twitter_username
        form.is_twitter_visible.data = g.user.profile.is_twitter_visible
        form.website.data = g.user.profile.website
    return render_template('user/settings_profile.html',
        form = form,
        title = 'Account Settings for' + g.user.username)

@app.route('/settings/emails/', methods = ['GET', 'POST'])
@login_required
def settings_emails():
    form = SettingsEmailsForm()
    if form.validate_on_submit():
        return redirect(url_for('settings_emails_add_email', email = form.email.data))
    return render_template('user/settings_emails.html',
        form = form, 
        title = 'Manage Emails')

@app.route('/settings/emails/add/<email>/')
@login_required
def settings_emails_add_email(email = None):
    if email != None and Functions.is_email(email):
        email_object = Email.get_email_by_email(email)
        if email_object == None:
            email = Email(email = email, user_id = g.user.id)
            db.session.add(email)
            db.session.commit()
            email_verification(email)
            flash('%s has been successfully added.' % (email.email)) 
        else:
            if email_object.user == g.user:
                flash('%s is already added.' % (email_object.email)) 
            else:
                flash('%s registered by another user.' % (email_object.email)) 
    return redirect(url_for('settings_emails'))

@app.route('/settings/emails/delete/<email>/')
@login_required
def settings_emails_delete_email(email = None):
    if email != None and Functions.is_email(email):
        email = Email.get_email_by_email(email)
        if email == None:
            flash('Unregistered email cannot be deleted.')
        elif email not in g.user.emails:
            flash('%s is not your email. You cannot delete it.' % (email.email)) 
        elif email.is_primary:
            flash('%s is your primary email. It cannot be deleted.' % (email.email))
        else:
            email.make_deleted()
            db.session.add(email)
            db.session.commit()
            flash('%s has been successfully deleted.' % (email.email))
    return redirect(url_for('settings_emails'))

@app.route('/settings/emails/make-primary/<email>/')
@login_required
def settings_emails_make_primary_email(email = None):
    if email != None and Functions.is_email(email):
        email = Email.get_email_by_email(email)
        if email == None:
            flash('Unregistered email cannot be primary email.')
        elif email not in g.user.emails:
            flash('%s is not registered by your account.' % (email.email))
        elif email.is_primary:
            flash('%s is already your primary email.' % (email.email))
        elif email.is_not_verified():
            flash('%s is not a verified email. Please verify to make primary.' % (email.email))
        else:
            current_primary_email = g.user.get_primary_email()
            current_primary_email.is_primary = False
            db.session.add(current_primary_email)
            email.make_primary()
            db.session.add(email)
            db.session.commit()
            flash('%s has been successfully made your primary email.' % (email.email))
    return redirect(url_for('settings_emails'))

@app.route('/settings/emails/request-key/<email>/')
@login_required
def settings_emails_request_key_email(email = None):
    if email == None or not Functions.is_email(email):
        pass
    else:
        email = Email.get_email_by_email(email)
        if email == None:
            pass
        elif email not in g.user.emails:
            pass
        elif email.is_not_verified():
            email_verification(email)
            flash('We sent your email verification to %s. Please check your inbox for verification instructions.' % (email.email))
        elif email.is_verified():
            flash('%s is already verified.' % (email.email))
        elif email.is_reported():
            flash('%s is reported. It cannot be verified until case is resolved.' % (email.email))
    return redirect(url_for('settings_emails'))

@app.route('/settings/emails/verify/<email>/')
@login_required
def settings_emails_verify_email(email = None):
    if email == None or not Functions.is_email(email):
        pass
    elif request.args.get("key") == None or len(request.args.get("key")) != 32:
        flash('Verification key could not be detected. You may have a broken link.')
    else:
        email = Email.get_email_by_email(email)
        if email == None:
            flash('Unregistered email cannot be verified.')
        elif email not in g.user.emails:
            flash('%s is not your email. If you own this email, please send an email to \'emails@thankspress.com\'' % (email.email)) 
        elif email.is_verified():
            flash('%s is already verified.' % (email.email))
        elif email.is_reported():
            flash('%s is reported. It cannot be verified until case is resolved.' % (email.email))
        else:
            if email.verification_key == request.args.get("key"):
                email.make_verified()
                db.session.add(email)
                db.session.commit()
                flash('%s has been successfully verified.' % (email.email))
            else:
                flash('Verification key is not valid. Please request a new verification key and try again.')
    return redirect(url_for('settings_emails'))

# Timeline -------------------------------------------------

@app.route('/')
def news_feed():
    return render_template('user/news_feed.html',
        title = 'news-feed',
        message = '/news-feed')

# User Pages -----------------------------------------------

@app.route('/<username>/')
@app.route('/<username>/timeline/')
def user_timeline(username = None):
    user = User.get_user_by_username(username)
    if user != None and user.is_active():
        return render_template('user/user_timeline.html',
            Follow = Follow,
            user = user,
            title = user.username + "'s Timeline")
    return render_template('404.html'), 404

@app.route('/<username>/following/')
def user_following(username = None):
    if username != None:
        user = User.get_user_by_username(username)
        if user != None and user.is_active():
            return render_template('user/user_following.html', 
                title = user.username + ' is following them.',
                message = '/' + user.username + '/following')
    return render_template('404.html'), 404

@app.route('/<username>/followers/')
def user_followers(username = None):
    if username != None:
        user = User.get_user_by_username(username)
        if user != None and user.is_active():
            return render_template('user/user_followers.html', 
                title = 'They are following' + user.username,
                message = '/' + user.username + '/followers')
    return render_template('404.html'), 404

@app.route('/<username>/thanks-given/')
def user_thanks_given(username = None):
    if username != None:
        user = User.get_user_by_username(username)
        if user != None and user.is_active():
            return render_template('user/user_thanks_given.html', 
                title = 'Thanks Given by' + user.username,
                message = '/' + user.username + '/thanks-given')
    return render_template('404.html'), 404

@app.route('/<username>/thanks-received/')
def user_thanks_received(username = None):
    if username != None:
        user = User.get_user_by_username(username)
        if user != None and user.is_active():
            return render_template('user/user_thanks_received.html', 
                title = 'Thanks received by' + user.username,
                message = '/' + user.username + '/thanks-received')
    return render_template('404.html'), 404

# User Follows ---------------------------------------------

@app.route('/users/follow/<int:followed_id>/')
@login_required
def user_follow(followed_id):
    user = User.get_user(followed_id)
    if user != None and not user.is_deleted():
        if not Follow.is_following_by_follower_and_followed(g.user.id, user.id):
            follow = Follow(g.user.id, user.id)
            db.session.add(follow)
            db.session.commit()
            follower_notification(g.user, user)
        return redirect(url_for('user_timeline', username = user.username))
    return render_template('404.html'), 404

@app.route('/users/unfollow/<int:followed_id>/')
@login_required
def user_unfollow(followed_id):
    user = User.get_user(followed_id)
    if user != None and not user.is_deleted():
        follow = Follow.get_follow_by_follower_and_followed(g.user.id, user.id)
        if follow != None:
            follow.make_deleted()
            db.session.add(follow)
            db.session.commit()
        return redirect(url_for('user_timeline', username = user.username))
    return render_template('404.html'), 404

# User ID Redirects ------------------------------------------

@app.route('/users/<int:user_id>/')
@app.route('/users/<int:user_id>/timeline/')
def users_user_timeline(user_id = None):
    try:
        return redirect(url_for('user_timeline', username = User.get_user(user_id).username))
    except:
        return render_template('404.html'), 404

@app.route('/users/<int:user_id>/followers/')
def users_user_followers(user_id = None):
    try:
        return redirect(url_for('user_followers', username = User.get_user(user_id).username))
    except:
        return render_template('404.html'), 404

@app.route('/users/<int:user_id>/following/')
def users_user_following(user_id = None):
    try:
        return redirect(url_for('user_following', username = User.get_user(user_id).username))
    except:
        return render_template('404.html'), 404

@app.route('/users/<int:user_id>/thanks-given/')
def users_user_thanks_given(user_id = None):
    try:
        return redirect(url_for('user_thanks_given', username = User.get_user(user_id).username))
    except:
        return render_template('404.html'), 404

@app.route('/users/<int:user_id>/thanks-received/')
def users_user_thanks_received(user_id = None):
    try:
        return redirect(url_for('user_thanks_received', username = User.get_user(user_id).username))
    except:
        return render_template('404.html'), 404

# ERROR Handlers ------------------------------------------

@app.errorhandler(404)
def internal_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('user/500.html'), 500
