from quart import Blueprint, render_template, session, request, redirect, url_for, flash, send_from_directory
from src.forms import ContactForm
from src.services import MailService

bp = Blueprint('home', __name__)


@bp.route("/")
async def home():
    if 'theme' not in session:
        session['theme'] = "lavender-dark"
    return await render_template('home.html')


@bp.route("/termsofservice", methods=["GET"])
async def terms_of_service():
    return await render_template("legal/terms_of_service.html")


@bp.route("/privacy", methods=["GET"])
async def privacy_policy():
    return await render_template("legal/privacy_policy.html")


@bp.route("/contact", methods=['GET', "POST"])
async def contact():
    form = ContactForm()
    if await request.method == "GET":
        return await render_template('contact/contact.html', form=form)

    if await request.method == "POST":

        if form.validate_on_submit():
            # You can now access form.first_name.data, etc.
            MailService.send_generic_inquiry_email(email=form.email.data, first_name=form.first_name.data,
                                                   last_name=form.last_name.data, message=form.message.data,
                                                   phone_number=form.phone.data)
            await flash("Thank you! Your message has been received. A confirmation email has been sent to you.", "success")
            return redirect(url_for("home.contact"))

        else:
            await flash("❌ There were errors in your form. Please correct them and try again.", "error")
            return await render_template('contact/contact.html', form=form)
