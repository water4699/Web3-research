-- 更新 SurfAccount 表结构，支持邮箱验证码登录
-- 执行此脚本前请备份数据库！

-- 1. 重命名旧的密码字段
ALTER TABLE surf_accounts CHANGE COLUMN password_encrypted email_password_encrypted TEXT;

-- 2. 添加邮箱服务器配置字段
ALTER TABLE surf_accounts ADD COLUMN email_server VARCHAR(100) DEFAULT 'imap.gmail.com' AFTER email;
ALTER TABLE surf_accounts ADD COLUMN email_port INT DEFAULT 993 AFTER email_server;

-- 3. 更新现有数据（如果有的话）
-- 注意：现有的 email_password_encrypted 字段需要手动更新为邮箱密码
-- UPDATE surf_accounts SET email_server = 'imap.gmail.com', email_port = 993 WHERE email_server IS NULL;

-- 4. 查看更新后的表结构
DESCRIBE surf_accounts;

