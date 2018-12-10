from datetime import datetime
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, PostForm, \
    ResetPasswordRequestForm, ResetPasswordForm, AddAddressForm, FollowAddressForm, ExploreAddressForm, NewTxSeenForm, MainSearchForm
from app.models import User, Post, Address, Comment
from app.email import send_password_reset_email
from app.blockchain import BitcoinAddress, build

##############################

@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        return redirect(url_for('index'))
    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='Home', form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)

@app.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='Explore', posts=posts.items,
                           next_url=next_url, prev_url=prev_url)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)    

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)

@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('user', username=user.username, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('user', username=user.username, page=posts.prev_num) \
        if posts.has_prev else None
    
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url, title="Profile")

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)

@app.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are following {}!'.format(username))
    return redirect(url_for('user', username=username))

@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are not following {}.'.format(username))
    return redirect(url_for('user', username=username))

@app.route('/track/<addresse>')
@login_required
def track_address(addresse):
    if Address.query.filter_by(address=addresse).scalar() is None:
        address1 = build(addresse)
        address2 = Address(address=address1.address, comment=address1.comment, n_tx=address1.n_tx,
        total_received=address1.total_received, last_tx=datetime.utcfromtimestamp(address1.last_tx_date), author=current_user, total_sent=address1.total_sent, balance=address1.balance)
        db.session.add(address2)
        db.session.commit()
    addressquery = Address.query.filter_by(address=addresse).first()
    if addressquery is None:
        flash('Address not found')
    current_user.track_address(addressquery)
    db.session.commit()
    flash('You are now tracking {}!'.format(addresse))
    
    return redirect(url_for('show_address_details', address=addresse, addressobj = addressquery))

@app.route('/untrack/<addresse>')
@login_required
def untrack_address(addresse):
    address1 = Address.query.filter_by(address=addresse).first()
    if address1 is None:
        flash('Address {} not found.'.format(addresse))
        return redirect(url_for('show_address_details', address=addresse))
    
    current_user.untrack_address(address1)
    db.session.commit()
    flash('You are not tracking {} any more.'.format(addresse))
    return redirect(url_for('show_address_details', address=addresse, addressobj = address1))

@app.route('/addresses', methods=['GET'])
@login_required
def show_tracked_addresses():
    return render_template('address.html', title='My addresses', 
                           addresses=current_user.tracked_addresses())

@app.route('/newtx/delete', methods=['GET'])
@login_required
def show_newtx_delet():
    x = current_user.reset_tracked_addresses_with_new_tx()
    for i in x:
        i.new_tx = 0
    db.session.merge(i)
    return render_template('newtx.html', title='New transactions', 
                        addresses=current_user.tracked_addresses_with_new_tx())
    

@app.route('/newtx', methods=['GET', 'POST'])
@login_required
def show_newtx():
    form = NewTxSeenForm()
    if form.validate_on_submit():
        
        db.session.commit()
    return render_template('newtx.html', title='New transactions', 
                           addresses=current_user.tracked_addresses_with_new_tx(), form=form)


@app.route('/blockexplorer')
def block_explorer():
    form = ExploreAddressForm()
    mainform = MainSearchForm()
    addressget = request.args.get('address', type=str)
    if addressget:
        try:
            address = addressget.replace(' ', '')
            address2 = build(address)
            addressquery = Address.query.filter_by(address=addressget).first()
            if address2.last_tx_date == 0:
                last_tx_data = " - "
            else:
                last_tx_data = datetime.fromtimestamp(address2.last_tx_date).strftime('%Y-%m-%d %H:%M:%S')
            transactionlist = []
            for i in address2.transactions:
                x = datetime.fromtimestamp(i.time).strftime('%Y-%m-%d %H:%M:%S')
                i.time = x
                transactionlist.append(i)

            return render_template('addressdetails.html', title='Details', address=address2.address, n_tx=address2.n_tx, last_tx=last_tx_data, balance=address2.balance, transactions=transactionlist, addressobj=addressquery)
        except:
            flash("Address not found... Please check the address and try again")
    return render_template('blockexplorer.html', title='Explorer', form=form, mainform=mainform)
    
@app.route('/blockexplorer/address/<address>', methods=['GET'])
def show_address_details(address):
    form = ExploreAddressForm()
    
    if address:
        try:
            address1 = build(address)
            addressquery = Address.query.filter_by(address=address).first()
            #Formatting Last TX time
            if address1.last_tx_date == 0:
                last_tx_data = " - "
            else:
                last_tx_data = datetime.fromtimestamp(address1.last_tx_date).strftime('%Y-%m-%d %H:%M:%S')
            transactionlist = []
            # Formatting the TX Time
            for i in address1.transactions:
                x = datetime.fromtimestamp(i.time).strftime('%Y-%m-%d %H:%M:%S')
                i.time = x
                transactionlist.append(i)
            
            return render_template('addressdetails.html', title='Details', address=address1.address, n_tx=address1.n_tx, last_tx=last_tx_data, balance=address1.balance, transactions=transactionlist, addressobj = addressquery)
        except:
            flash("Address not found... Please check the address and try again")
            
    return render_template('blockexplorer.html', title='Explorer', form=form)