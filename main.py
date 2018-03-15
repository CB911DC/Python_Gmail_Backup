"""
Dumps a mailbox and uploads the email structure to s3
Required environment variables:
EMAIL_SERVER
EMAIL_ADDRESS
EMAIL_PASS
S3_BUCKET
"""
import logging
import imaplib
import os
import boto3

class emailBackup(object):
    """For backing up email from a mailbox, probably to s3"""
    def __init__(self, email_address):
        self.s3 = boto3.client('s3')
        self.email_address = email_address
        target_dir = os.getenv('TARGET_DIR')
        self.target_dir = target_dir or os.path.join(os.path.abspath('.'), self.email_address)
        if not os.path.isdir(self.target_dir):
                os.mkdir(self.target_dir)

    def _login(self, server, passwd):
        """Login to the mailserver"""
        act = imaplib.IMAP4_SSL(server)
        try:
            act.login(self.email_address, passwd)
        except imaplib.IMAP4.error as err:
            if 'Please log in via your web browser' in err.args[0].decode('utf8'):
                logging.error('Please login to the google account and enable less secure apps!')
                raise
            else:
                raise
        return act

    def _process_mailbox(self, act, folder):
        """Dump all emails in the folder to files in output directory."""
        response, data = act.search(None, "ALL")
        if response != 'OK':
            logging.info('No messages found!')  
            return
        data = data[0].decode('utf-8')
        for num in data.split():
            response, data = act.fetch(num, '(RFC822)')
            if response != 'OK':
                logging.error('ERROR getting message {}'.format(num))
                return
            logging.info('Writing message {}'.format(num))
            email_target = os.path.join(self.target_dir, folder).replace('/', '_')
            if not os.path.isdir(email_target):
                os.mkdir(email_target)
            with open(os.path.join(email_target, '{}.eml'.format(num)), 'wb') as file:
                file.write(data[0][1])
        return

    def get_mail(self, server, passwd):
        """Retrieves mail from the server"""
        act = self._login(server, passwd)
        response, data = act.list()
        if response != 'OK':
            raise ValueError('ERROR getting list of folders!')
        logging.info('Logged in, processing mailbox...')
        for folder in data:
            foldername = folder.decode('utf-8').split("\"")[-2]
            logging.info('processing mail for {}'.format(foldername))
            if foldername == '[Gmail]':
                continue
            response, data = act.select('"{}"'.format(foldername))
            if response != 'OK':
                raise ValueError('Unable to open mailbox!  Details: {}'.format(response))
            logging.info('Processing messages for folder {}'.format(foldername))
            self._process_mailbox(act, foldername)
        act.close()

    def upload_to_s3(self, s3_bucket):
        """Upload the mail dir to s3"""
        for root, dirs, files in os.walk(self.target_dir):
            for filename in files:
                # construct the full local path
                local_path = os.path.join(root, filename)
                # construct the full Dropbox path
                relative_path = os.path.relpath(local_path, self.target_dir)
                s3_path = os.path.join(s3_bucket, self.email_address, relative_path)
                logging.info('Uploading {}...'.format(s3_path))
                self.s3.upload_file(local_path, s3_bucket, s3_path)


if __name__ == "__main__":
	server = os.getenv('EMAIL_SERVER')
	user = os.getenv('EMAIL_ADDRESS')
	passwd = os.getenv('EMAIL_PASS')
	s3_bucket = os.getenv('S3_BUCKET')
	if not all((server, user, passwd, s3_bucket)):
	    raise ValueError('One or more required environment variables not set!')
	logger = logging.getLogger()
	logger.setLevel(logging.INFO)
	email = emailBackup(user)
	email.get_mail(server, passwd)
	email.upload_to_s3(s3_bucket)