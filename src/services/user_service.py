class UserService:

    @staticmethod
    def create_access_token():
        # create a 10 letter token
        import random
        import string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=10))
