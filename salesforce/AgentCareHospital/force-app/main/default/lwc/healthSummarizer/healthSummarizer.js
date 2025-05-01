import { LightningElement, track, api, wire } from 'lwc';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';
import { createRecord, updateRecord } from 'lightning/uiRecordApi';
import { NavigationMixin } from 'lightning/navigation';
import { getRecord } from 'lightning/uiRecordApi';

// Import Apex methods
import summarizeHealthReport from '@salesforce/apex/HealthSummarizer.summarizeHealthReport';
import summarizeHealthReports from '@salesforce/apex/HealthSummarizer.summarizeHealthReports';
import updateHealthSummary from '@salesforce/apex/HealthSummarizer.updateHealthSummary';
import extractTextFromFile from '@salesforce/apex/HealthSummarizer.extractTextFromFile';

export default class HealthSummarizer extends NavigationMixin(LightningElement) {
    @api recordId; // Health Summary Id if coming from a record page
    @track healthSummaryId;
    @track healthReports = [];
    @track uploadedFiles = [];
    @track isLoading = false;
    @track summaryText = '';
    @track recommendationsText = '';
    @track patientName = '';
    
    // Fields for new health report
    @track newReportName = '';
    @track newReportType = 'Lab Test';
    @track newReportContent = '';
    
    // Report type options
    get reportTypeOptions() {
        return [
            { label: 'Lab Test', value: 'Lab Test' },
            { label: 'Imaging', value: 'Imaging' },
            { label: 'Doctor Note', value: 'Doctor Note' },
            { label: 'Prescription', value: 'Prescription' },
            { label: 'Other', value: 'Other' }
        ];
    }
    
    connectedCallback() {
        // If recordId is provided, we're on a Health Summary record page
        if (this.recordId) {
            this.healthSummaryId = this.recordId;
            this.loadHealthReports();
        }
    }
    
    // Method to handle file upload
    handleFileUpload(event) {
        const uploadedFiles = event.detail.files;
        this.isLoading = true;
        
        Promise.all(
            uploadedFiles.map(file => {
                return extractTextFromFile({ contentDocumentId: file.documentId })
                    .then(extractedText => {
                        this.newReportContent = extractedText;
                        return { name: file.name, documentId: file.documentId, content: extractedText };
                    });
            })
        )
        .then(results => {
            this.uploadedFiles = results;
            this.isLoading = false;
            this.showToast('Success', 'Files uploaded successfully', 'success');
        })
        .catch(error => {
            this.isLoading = false;
            this.showToast('Error', 'Error uploading files: ' + error.message, 'error');
        });
    }
    
    // Method to create a new Health Summary
    createHealthSummary() {
        if (!this.patientName) {
            this.showToast('Error', 'Please enter a patient name', 'error');
            return;
        }
        
        this.isLoading = true;
        
        const fields = {
            'Patient_Name__c': this.patientName,
            'Summary_Date__c': new Date().toISOString(),
            'Status__c': 'New'
        };
        
        const recordInput = { apiName: 'Health_Summary__c', fields };
        
        createRecord(recordInput)
            .then(healthSummary => {
                this.healthSummaryId = healthSummary.id;
                this.showToast('Success', 'Health Summary created', 'success');
                this.isLoading = false;
            })
            .catch(error => {
                this.showToast('Error', 'Error creating Health Summary: ' + error.message, 'error');
                this.isLoading = false;
            });
    }
    
    // Method to create a new Health Report
    createHealthReport() {
        if (!this.healthSummaryId) {
            this.showToast('Error', 'Please create a Health Summary first', 'error');
            return;
        }
        
        if (!this.newReportName) {
            this.showToast('Error', 'Please enter a report name', 'error');
            return;
        }
        
        this.isLoading = true;
        
        const fields = {
            'Report_Name__c': this.newReportName,
            'Report_Date__c': new Date().toISOString(),
            'Report_Type__c': this.newReportType,
            'Report_Content__c': this.newReportContent,
            'Health_Summary__c': this.healthSummaryId
        };
        
        const recordInput = { apiName: 'Health_Report__c', fields };
        
        createRecord(recordInput)
            .then(healthReport => {
                this.loadHealthReports();
                this.newReportName = '';
                this.newReportContent = '';
                this.showToast('Success', 'Health Report created', 'success');
                this.isLoading = false;
            })
            .catch(error => {
                this.showToast('Error', 'Error creating Health Report: ' + error.message, 'error');
                this.isLoading = false;
            });
    }
    
    // Method to load Health Reports
    loadHealthReports() {
        if (!this.healthSummaryId) return;
        
        this.isLoading = true;
        
        // Query to get Health Reports related to this Health Summary
        // This would be an Apex method in a real implementation
        this.isLoading = false;
        
        // Placeholder for demo purposes
        this.healthReports = [
            { id: 'demo1', name: 'Recent Blood Test', type: 'Lab Test', date: new Date().toLocaleDateString() },
            { id: 'demo2', name: 'Chest X-Ray', type: 'Imaging', date: new Date().toLocaleDateString() }
        ];
    }
    
    // Method to generate summary
    generateSummary() {
        if (this.healthReports.length === 0) {
            this.showToast('Error', 'No health reports available to summarize', 'error');
            return;
        }
        
        this.isLoading = true;
        
        // In a real implementation, you would pass actual report IDs
        const reportIds = this.healthReports.map(report => report.id);
        
        updateHealthSummary({ 
            healthSummaryId: this.healthSummaryId, 
            healthReportIds: reportIds 
        })
        .then(() => {
            this.isLoading = false;
            this.showToast('Success', 'Health summary generated successfully', 'success');
        })
        .catch(error => {
            this.isLoading = false;
            this.showToast('Error', 'Error generating summary: ' + error.message, 'error');
        });
    }
    
    // Helper method to show toast notifications
    showToast(title, message, variant) {
        const event = new ShowToastEvent({
            title: title,
            message: message,
            variant: variant
        });
        this.dispatchEvent(event);
    }
    
    // Event handlers for form inputs
    handlePatientNameChange(event) {
        this.patientName = event.target.value;
    }
    
    handleReportNameChange(event) {
        this.newReportName = event.target.value;
    }
    
    handleReportTypeChange(event) {
        this.newReportType = event.target.value;
    }
    
    handleReportContentChange(event) {
        this.newReportContent = event.target.value;
    }
    
    // Navigation methods
    viewHealthSummary() {
        if (!this.healthSummaryId) return;
        
        this[NavigationMixin.Navigate]({
            type: 'standard__recordPage',
            attributes: {
                recordId: this.healthSummaryId,
                objectApiName: 'Health_Summary__c',
                actionName: 'view'
            }
        });
    }
}