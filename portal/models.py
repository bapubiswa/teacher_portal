from django.db import models

class Teacher(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True)
    password_hash = models.TextField()
    salt = models.TextField()
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'teachers'
        managed = False

class Student(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=100)
    marks = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'students'
        managed = False
        unique_together = ('name', 'subject')

class AuditLog(models.Model):
    id = models.AutoField(primary_key=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    action = models.CharField(max_length=20)
    old_marks = models.IntegerField(null=True)
    new_marks = models.IntegerField(null=True)
    timestamp = models.DateTimeField()

    class Meta:
        db_table = 'audit_log'
        managed = False
