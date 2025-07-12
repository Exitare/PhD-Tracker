CREATE TABLE stripe_webhook_events (
	id INTEGER NOT NULL, 
	event_id VARCHAR(100) NOT NULL, 
	event_type VARCHAR(100) NOT NULL, 
	received_at BIGINT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (event_id)
);

CREATE TABLE users (
	id INTEGER NOT NULL, 
	stripe_customer_id VARCHAR, 
	email VARCHAR(150) NOT NULL, 
	email_verified BOOLEAN NOT NULL, 
	email_verified_at BIGINT, 
	first_name VARCHAR(150), 
	last_name VARCHAR(150), 
	last_sign_in BIGINT NOT NULL, 
	organization_name VARCHAR(150), 
	managed_by INTEGER, 
	managed_by_stripe_id VARCHAR(100), 
	pending_email VARCHAR(150), 
	password_hash VARCHAR(200) NOT NULL, 
	created_at BIGINT NOT NULL, 
	active BOOLEAN NOT NULL, 
	deactivated_at BIGINT, 
	"plan" VARCHAR(50), 
	stripe_subscription_id VARCHAR, 
	stripe_subscription_item_ids VARCHAR, 
	stripe_subscription_expires_at BIGINT, 
	stripe_subscription_canceled BOOLEAN NOT NULL, 
	role VARCHAR(7) NOT NULL, 
	access_code VARCHAR(100), 
	PRIMARY KEY (id), 
	UNIQUE (stripe_customer_id), 
	UNIQUE (email), 
	FOREIGN KEY(managed_by) REFERENCES users (id)
);

CREATE TABLE projects (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	description TEXT NOT NULL, 
	type VARCHAR(12) NOT NULL, 
	selected_venue VARCHAR(255), 
	selected_venue_url VARCHAR(255), 
	journal_recommendations JSON, 
	venue_requirements TEXT, 
	created_at BIGINT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE usage_logs (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	event_name VARCHAR(100) NOT NULL, 
	used_tokens INTEGER NOT NULL, 
	created_at BIGINT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE sub_projects (
	id INTEGER NOT NULL, 
	project_id INTEGER NOT NULL, 
	type VARCHAR(8) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	reviewer_comments TEXT, 
	description TEXT NOT NULL, 
	created_at BIGINT NOT NULL, 
	deadline BIGINT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id)
);

CREATE TABLE milestones (
	id INTEGER NOT NULL, 
	sub_project_id INTEGER NOT NULL, 
	milestone TEXT NOT NULL, 
	due_date VARCHAR(10) NOT NULL, 
	notes TEXT, 
	status VARCHAR(50), 
	PRIMARY KEY (id), 
	FOREIGN KEY(sub_project_id) REFERENCES sub_projects (id)
);

