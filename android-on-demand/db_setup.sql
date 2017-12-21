/*create db*/
CREATE DATABASE slack_bot_circleci;
/*selected created db*/
USE slack_bot_circleci;
/*create tablein database*/
CREATE TABLE slack_bot_android_on_demand ( id  varchar(50) not null,fork  boolean not null default 0,fork_name varchar(200),branch_name varchar(200),rb boolean not null default 0,db boolean not null default 0,ob boolean not null default 0,bb boolean not null default 0,ddb boolean not null default 0, rdb boolean not null default 0,cdrb boolean not null default 0,ut boolean not null default 0,ub boolean not null default 0,leakcanary boolean not null default 0);