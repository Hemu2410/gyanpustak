-- =========================
-- UNIVERSITIES
-- =========================
INSERT INTO UNIVERSITY (name, address, rep_first_name, rep_last_name, rep_email, rep_phone) VALUES
('IIT Delhi', 'Hauz Khas, New Delhi', 'Amit', 'Sharma', 'amit@iitd.ac.in', '9876543210'),
('IIT Bombay', 'Powai, Mumbai', 'Priya', 'Patel', 'priya@iitb.ac.in', '9876543211'),
('NIT Trichy', 'Tiruchirappalli, Tamil Nadu', 'Ravi', 'Kumar', 'ravi@nitt.edu', '9876543212');

-- =========================
-- USERS
-- =========================
INSERT INTO USER (name, Email, password, phone, address, University_id, user_type) VALUES
('Super Admin', 'superadmin@gyanpustak.com', 'scrypt:32768:8:1$L8Zg9P2t3LYQgtEB$e4d07ae052f7ff47eb8bc9844df8c122ae8b8957c424107e1ea09212576812d14e2ea81aaac677c76f5d009dc79a9442591462301e54c1ea309ec71c3667c79c', NULL, NULL, NULL, 'super_admin'),
('Admin User', 'admin@gyanpustak.com', 'scrypt:32768:8:1$L8Zg9P2t3LYQgtEB$e4d07ae052f7ff47eb8bc9844df8c122ae8b8957c424107e1ea09212576812d14e2ea81aaac677c76f5d009dc79a9442591462301e54c1ea309ec71c3667c79c', '9000000001', 'GyanPustak HQ', NULL, 'admin'),
('Support Agent', 'support@gyanpustak.com', 'scrypt:32768:8:1$Jkuft7R0Fs0xJEWw$926276330aee82b022422b1de993029765b07b0b469fcef4dbfd7bad5b45cc567f3afc8b33287514d571dbc23d9186ad13e5279f416b2da8f3060cb0e649c7de', '9000000002', 'GyanPustak HQ', NULL, 'customer_support'),
('Rahul', 'rahul@student.com', 'scrypt:32768:8:1$zPy4bYjrGVLoLcKN$11f7ea4bff84f750e6185879d2c731a705b39856e1263d6af36b76fb3979e59a11f5f51b2329f5de25e5fa561a68bf3bb888d60cd1646ccd0ae2218a9524189c', '8888888888', 'IIT Bhubaneswar', NULL, 'student');

-- =========================
-- EMPLOYEE
-- =========================
INSERT INTO EMPLOYEE (User_id, emp_id, salary, gender, aadhaar) VALUES
(1, 'EMP001', 120000, 'Male', '111111111111'),
(2, 'EMP002', 90000, 'Male', '222222222222'),
(3, 'EMP003', 60000, 'Female', '333333333333');

-- =========================
-- ROLES
-- =========================
INSERT INTO ADMIN (User_id) VALUES (1), (2);
INSERT INTO SUPER_ADMIN (id, User_id) VALUES (1, 1);
INSERT INTO CUSTOMER_SUPPORT (User_id) VALUES (3);

-- =========================
-- STUDENTS
-- =========================
INSERT INTO STUDENT (User_id, dob, status, major, year_of_study) VALUES
(4, '2002-05-15', 'undergraduate', 'Computer Science', 2);

-- =========================
-- DEPARTMENTS
-- =========================
INSERT INTO DEPARTMENT (name, University_id) VALUES
('Computer Science', 1), ('Electronics', 1), ('Mathematics', 1),
('Computer Science', 2), ('Mechanical', 2),
('Computer Science', 3), ('Civil', 3);

-- =========================
-- INSTRUCTORS
-- =========================
INSERT INTO INSTRUCTOR (name, University_id, Dept_id) VALUES
('Dr. S. Arora', 1, 1),
('Dr. R. Mehta', 1, 2),
('Dr. K. Singh', 2, 4),
('Dr. P. Nair', 3, 6);

-- =========================
-- COURSES
-- =========================
INSERT INTO COURSE (name, semester, year) VALUES
('Data Structures', 'Fall', 2025),
('Database Systems', 'Fall', 2025),
('Operating Systems', 'Spring', 2025),
('Machine Learning', 'Fall', 2025),
('Digital Electronics', 'Spring', 2025),
('Thermodynamics', 'Fall', 2025);

-- =========================
-- TEACHES
-- =========================
INSERT INTO TEACHES (Instructor_id, Course_id) VALUES
(1,1),(1,2),(2,5),(3,4),(4,6);

-- =========================
-- OFFERS
-- =========================
INSERT INTO OFFERS (Dept_id, Course_id) VALUES
(1,1),(1,2),(2,5),(4,3),(4,4),(5,6),(6,1);

-- =========================
-- BOOKS
-- =========================
INSERT INTO BOOK (title, price, isbn, publisher, pub_date, edition, language, format, type, purchase_option, quantity, category, subcategory, authors, keywords) VALUES
('Introduction to Algorithms', 899.00, '978-0262033848', 'MIT Press', '2009-07-31', 3, 'English', 'hardcover', 'new', 'buy', 50, 'Computer Science', 'Algorithms', 'Thomas H. Cormen, Charles E. Leiserson', 'algorithms,data structures,programming'),
('Database System Concepts', 750.00, '978-0078022159', 'McGraw Hill', '2019-02-15', 7, 'English', 'hardcover', 'new', 'buy', 35, 'Computer Science', 'Databases', 'Abraham Silberschatz, Henry Korth', 'database,sql,relational'),
('Operating System Concepts', 680.00, '978-1119800361', 'Wiley', '2021-05-01', 10, 'English', 'softcover', 'new', 'buy', 40, 'Computer Science', 'Operating Systems', 'Abraham Silberschatz, Peter Galvin', 'os,processes,memory'),
('Digital Design', 550.00, '978-0134549897', 'Pearson', '2018-03-10', 6, 'English', 'hardcover', 'new', 'buy', 30, 'Electronics', 'Digital', 'M. Morris Mano', 'digital,logic,circuits'),
('Introduction to Machine Learning', 1200.00, '978-0262043793', 'MIT Press', '2020-01-01', 4, 'English', 'hardcover', 'new', 'buy', 20, 'Computer Science', 'AI/ML', 'Ethem Alpaydin', 'machine learning,ai,neural networks'),
('Engineering Thermodynamics', 450.00, '978-8126541553', 'McGraw Hill', '2015-06-15', 8, 'English', 'softcover', 'used', 'buy', 25, 'Mechanical', 'Thermodynamics', 'P.K. Nag', 'thermo,heat,energy'),
('Python Programming', 399.00, '978-0134444321', 'Pearson', '2022-09-01', 3, 'English', 'electronic', 'new', 'rent', 100, 'Computer Science', 'Programming', 'John Zelle', 'python,programming,beginner'),
('Linear Algebra', 320.00, '978-0980232714', 'Wellesley-Cambridge', '2016-08-01', 5, 'English', 'softcover', 'used', 'rent', 15, 'Mathematics', 'Algebra', 'Gilbert Strang', 'linear algebra,matrices,vectors'),
('Computer Networks', 720.00, '978-0133594140', 'Pearson', '2021-01-10', 6, 'English', 'hardcover', 'new', 'buy', 28, 'Computer Science', 'Networks', 'Andrew Tanenbaum', 'networking,tcp,protocols'),
('Discrete Mathematics', 580.00, '978-0073383095', 'McGraw Hill', '2018-07-20', 8, 'English', 'hardcover', 'new', 'buy', 32, 'Mathematics', 'Discrete Math', 'Kenneth Rosen', 'discrete math,logic,graphs');

-- =========================
-- USES
-- =========================
INSERT INTO USES (Course_id, Book_id) VALUES
(1,1),(2,2),(3,3),(4,5),(5,4),(6,6),(1,10);

-- =========================
-- REVIEWS
-- =========================
INSERT INTO REVIEW (User_id, Book_id, rating, review_text) VALUES
(4, 1, 5, 'Excellent book for algorithms. A must-read for CS students.'),
(4, 2, 4, 'Very comprehensive coverage of database concepts.'),
(4, 4, 4, 'Great for understanding digital design fundamentals.'),
(4, 6, 3, 'Decent book but could use more practical examples.');

-- =========================
-- CART
-- =========================
INSERT INTO CART (User_id) VALUES (4);