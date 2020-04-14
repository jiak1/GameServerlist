from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField,IntegerField
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

	plugins = StringField('Plugins',validators=[Optional()])
	datapacks = StringField('Datapacks',validators=[Optional()])
	mods = StringField('Mods',validators=[Optional()])

	tags = StringField('Tags',validators=[Optional()])

	website = URLField('Website',validators=[Optional(),url(),Length(max=100)])
	discord = URLField('Discord',validators=[Optional(),Length(max=15)])

	trailer = URLField('Trailer',validators=[Optional(),Length(max=15)])

	rejectReason = StringField('Reject Reason')
	action = SubmitField('Action')
	#TODO: BANNER/IMAGES

	def validate_ip(self, ip):
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