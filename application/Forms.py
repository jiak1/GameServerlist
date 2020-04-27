from flask_wtf import FlaskForm,RecaptchaField,Recaptcha
from wtforms import StringField, PasswordField, BooleanField, SubmitField,IntegerField,HiddenField
from wtforms.fields.html5 import URLField
from wtforms.validators import DataRequired,ValidationError, Email, EqualTo,Length,url,Optional,NumberRange
from .Models import Account,Server
import safe


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegisterForm(FlaskForm):
	username = StringField('Username', validators=[DataRequired()])
	email = StringField('Email', validators=[DataRequired(), Email()])
	password = PasswordField('Password', validators=[DataRequired()])
	password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
	submit = SubmitField('Register')

	def validate_username(self, username):
		user = Account.query.filter_by(username=username.data).first()
		if user is not None:
			raise ValidationError('That username is already taken.')

	def validate_email(self, email):
		user = Account.query.filter_by(email=email.data).first()
		if user is not None:
			raise ValidationError('That email address is already in use.')
	
	def validate_password(self, password):
		strength = safe.check(password.data)
		if(strength == "terrible" or strength == "simple" or strength == "medium"):
			raise ValidationError('Please use a stronger password, ensure it has a capital letter, lower case and number.')

class ServerForm(FlaskForm):
	name = StringField('Name', validators=[DataRequired(),Length(min=5, max=50,message="Your server name needs to be between 5 and 50 characters.")])
	ip = StringField('IP', validators=[DataRequired(message="No IP was given."),Length(min=5, max=35,message="Invalid IP.")])
	port = IntegerField('Port',validators=[DataRequired(message="No port was given."),NumberRange(min=1, max=65535,message="Invalid port.")])
	country = StringField('Country',validators=[DataRequired(message="No Country was given."),Length(max=4)])
	
	description = StringField('Description', validators=[DataRequired(),Length(min=30,max=1000,message="The description needs to be between 30 & 1000 characters.")])

	serverType = StringField('ServerType', validators=[DataRequired(message="No Server Type was selected.")])
	banner = HiddenField('Banner')

	plugins = StringField('Plugins',validators=[Optional()])
	datapacks = StringField('Datapacks',validators=[Optional()])
	mods = StringField('Mods',validators=[Optional()])

	tags = StringField('Tags',validators=[Optional()])

	votifierEnabled = StringField('Votifier Status')
	votifierPort = IntegerField('Votifier Port',validators=[Optional(),DataRequired(message="No votifier port was given."),NumberRange(min=1, max=65535,message="Invalid votifier port.")])
	votifierToken = StringField('Votifier Public Key',validators=[Optional(),DataRequired(message="Please fill in the Votifier public key.")])

	website = URLField('Website',validators=[Optional(),Length(max=100)])
	discord = URLField('Discord',validators=[Optional(),Length(max=80)])

	trailer = URLField('Trailer',validators=[Optional(),Length(max=15)])

	rejectReason = StringField('Reject Reason')
	action = SubmitField('Action')

	isEdit = HiddenField('Is Edit')
	recaptcha = RecaptchaField(validators=[Recaptcha(message="You didn't prove you weren't a robot, please try again. 🤖")])


	def validate_ip(self, ip):
		if(self.isEdit.data == "N"):
			server = Server.query.filter_by(ip=ip.data, port=self.port.data).first()
			if server is not None:
				raise ValidationError('There is already a submission for this server, please check that the IP & Port are correct.')

class PasswordChangeForm(FlaskForm):
	password = PasswordField('Password', validators=[DataRequired()])
	newPassword = PasswordField('New Password', validators=[DataRequired(),EqualTo('newPassword2')])
	newPassword2 = PasswordField('Repeat New Password', validators=[DataRequired()])
	passwordSubmit = SubmitField('Change Password')

class EmailChangeForm(FlaskForm):
	oldEmail = PasswordField('Old Email', validators=[DataRequired()])
	newEmail = PasswordField('New Email', validators=[DataRequired()])
	emailSubmit = SubmitField('Change Email')

class ResetPasswordForm(FlaskForm):
	password = PasswordField('New Password', validators=[DataRequired()])
	password2 = PasswordField('Repeat New Password', validators=[DataRequired(), EqualTo('password')])
	submit = SubmitField('Change Password')

class VotifierTestForm(FlaskForm):
	ip = StringField('IP Address', validators=[DataRequired()])
	port = PasswordField('Votifier Port', validators=[DataRequired()])
	token = StringField('Public Key', validators=[DataRequired()])
	username = StringField('Username', validators=[DataRequired()])
	submit = SubmitField('Submit')

class AccountEmailChangeForm(FlaskForm):
	emailPassword = PasswordField('Password', validators=[DataRequired()])
	newEmail = StringField('New Email', validators=[DataRequired(),Email()])
	emailSubmit = SubmitField('Change Email')

	def validate_newEmail(self, newEmail):
		user = Account.query.filter_by(email=newEmail.data).first()
		if user is not None:
			raise ValidationError('That email address is already in use.')
	

class AccountUsernameChangeForm(FlaskForm):
	password = PasswordField('Password', validators=[DataRequired()])
	newUsername = StringField('New Username', validators=[DataRequired()])
	usernameSubmit = SubmitField('Change Username')

	def validate_newUsername(self, newUsername):
		user = Account.query.filter_by(username=newUsername.data).first()
		if user is not None:
			raise ValidationError('That username is already taken.')

class AccountPasswordChangeForm(FlaskForm):
	currentPassword = PasswordField('Current Password', validators=[DataRequired()])
	newPassword = PasswordField('New Password', validators=[DataRequired()])
	newPassword2 = PasswordField('Repeat New Password', validators=[DataRequired(), EqualTo('newPassword')])

	passwordSubmit = SubmitField('Change Password')
	
	def validate_newPassword(self, newPassword):
		strength = safe.check(newPassword.data)
		if(strength == "terrible" or strength == "simple" or strength == "medium"):
			raise ValidationError('Please use a stronger password, ensure it has a capital letter, lower case and number.')

class AccountGoogleLinkForm(FlaskForm):
	newUsername = StringField('New Username', validators=[DataRequired()])
	
	newPassword = PasswordField('New Password', validators=[DataRequired()])
	newPassword2 = PasswordField('Repeat New Password', validators=[DataRequired(), EqualTo('newPassword')])

	googleSubmit = SubmitField('Create Server List Account')

	def validate_newUsername(self, newUsername):
		user = Account.query.filter_by(username=newUsername.data).first()
		if user is not None:
			raise ValidationError('That username is already taken.')
			
	def validate_newPassword(self, newPassword):
		strength = safe.check(newPassword.data)
		if(strength == "terrible" or strength == "simple" or strength == "medium"):
			raise ValidationError('Please use a stronger password, ensure it has a capital letter, lower case and number.')

class AccountDeleteForm(FlaskForm):
	confirmEmail = PasswordField('Confirm Email', validators=[DataRequired(),Email()])
	confirmPassword = PasswordField('Confirm Password', validators=[Optional(),DataRequired()])

	deleteSubmit = SubmitField('Permanently Delete Account')

class ServerDeleteForm(FlaskForm):
	confirmName = StringField('Confirm Server Name', validators=[DataRequired()])

	deleteSubmit = SubmitField('Permanently Delete Server')

class TagsForm(FlaskForm):
	data = StringField('Tags To Add:', validators=[DataRequired()])
	submit = SubmitField('Add Tags')

class VoteForm(FlaskForm):
	username = StringField('Minecraft Username', validators=[DataRequired(message="Please enter your Minecraft Username."),Length(max=80,message="Username too long.")])
	voteSubmit = SubmitField('Vote')

class AdminServerForm(FlaskForm):
	name = StringField('Name', validators=[DataRequired(),Length(min=5, max=50,message="Your server name needs to be between 5 and 50 characters.")])
	ip = StringField('IP', validators=[DataRequired(message="No IP was given."),Length(min=5, max=35,message="Invalid IP.")])
	port = IntegerField('Port',validators=[DataRequired(message="No port was given."),NumberRange(min=1, max=65535,message="Invalid port.")])
	country = StringField('Country',validators=[DataRequired(message="No Country was given."),Length(max=4)])
	
	description = StringField('Description', validators=[DataRequired(),Length(min=30,max=1000,message="The description needs to be between 30 & 1000 characters.")])

	serverType = StringField('ServerType', validators=[DataRequired(message="No Server Type was selected.")])
	banner = StringField('Banner')

	plugins = StringField('Plugins',validators=[Optional()])
	datapacks = StringField('Datapacks',validators=[Optional()])
	mods = StringField('Mods',validators=[Optional()])

	tags = StringField('Tags',validators=[Optional()])

	votifierEnabled = StringField('Votifier Status')
	votifierPort = IntegerField('Votifier Port',validators=[Optional(),DataRequired(message="No votifier port was given."),NumberRange(min=1, max=65535,message="Invalid votifier port.")])
	votifierToken = StringField('Votifier Public Key',validators=[Optional(),DataRequired(message="Please fill in the Votifier public key.")])

	website = URLField('Website',validators=[Optional(),Length(max=100)])
	discord = URLField('Discord',validators=[Optional(),Length(max=80)])

	trailer = URLField('Trailer',validators=[Optional(),Length(max=15)])

	rejectReason = StringField('Reject Reason')
	action = SubmitField('Action')

	version = StringField('Server Version Results')
	displayVersion = StringField('Server Version Results')

	totalVotes = StringField('Total Votes')
	monthlyVotes = StringField('Monthly Votes')
	rank = StringField('Rank')

	playerCount = StringField('Current Player Count')
	playerMax = StringField('Max Players')

class ReportServerForm(FlaskForm):
	reason = StringField('Reason')
	description = StringField('Description',validators=[Length(max=1000,min=20)])

	recaptcha = RecaptchaField(validators=[Recaptcha(message="You didn't prove you weren't a robot, please try again. 🤖")])

	submit = SubmitField('Report')